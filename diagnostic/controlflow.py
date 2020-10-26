#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module provides functionality to create control flow graphs (deviation of https://pypi.org/project/pycfg/)."""

import ast
import re
import astor
import pygraphviz


class ControlFlowRegistry:
    registry = 0
    cache = {}

    @classmethod
    def register(cls, node):
        node.rid = cls.registry
        cls.cache[node.rid] = node
        cls.registry += 1
        return node.rid

    @classmethod
    def reset(cls):
        registry = 0
        cache = {}


class ControlFlowNode(dict):

    def __init__(self, parents=[], ast=None):
        self.rid = ControlFlowRegistry.register(self)

        self.parents = (parents[0] if isinstance(parents, tuple) else parents) or []
        self.ast_node = ast
        self.update_children(parents)  # requires self.rid
        self.children = []
        self.calls = []

    def __str__(self):
        return "id:%d line[%d] parents: %s : %s" % (self.rid, self.lineno(), str([p.rid for p in self.parents]), self.source())

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return self.rid == other.rid

    def __neq__(self, other):
        return self.rid != other.rid

    def lineno(self):
        return self.ast_node.lineno if hasattr(self.ast_node, "lineno") else 0

    def source(self):
        return astor.to_source(self.ast_node).strip()

    def to_json(self):
        return {"id":self.rid, "parents": [p.rid for p in self.parents], "children": [c.rid for c in self.children], "calls": self.calls, "at":self.lineno() ,"ast":self.source()}

    def set_parents(self, p):
        self.parents = p

    def add_parent(self, p):
        if p not in self.parents:
            self.parents.append(p)

    def add_parents(self, ps):
        for p in ps:
            self.add_parent(p)

    def add_calls(self, func):
        self.calls.append(func)

    def add_child(self, c):
        if c not in self.children:
            self.children.append(c)

    def update_children(self, parents):
        for p in parents:
            p.add_child(self)


class ControlFlow:

    def __init__(self):
        self.founder = ControlFlowNode(parents=[], ast=ast.parse("start").body[0]) # sentinel
        self.founder.ast_node.lineno = 0
        self.functions = {}
        self.functions_node = {}

    def parse(self, src):
        return ast.parse(src)

    def walk(self, node, myparents):
        fname = "on_%s" % node.__class__.__name__.lower()
        if hasattr(self, fname):
            fn = getattr(self, fname)
            v = fn(node, myparents)
            return v
        else:
            return myparents

    def on_module(self, node, myparents):
        """
        Module(stmt* body)
        """
        # each time a statement is executed unconditionally, make a link from
        # the result to next statement
        p = myparents
        for n in node.body:
            p = self.walk(n, p)
        return p

    def on_augassign(self, node, myparents):
        """
         AugAssign(expr target, operator op, expr value)
        """
        p = [ControlFlowNode(parents=myparents, ast=node)]
        p = self.walk(node.value, p)

        return p

    def on_annassign(self, node, myparents):
        """
        AnnAssign(expr target, expr annotation, expr? value, int simple)
        """
        p = [ControlFlowNode(parents=myparents, ast=node)]
        p = self.walk(node.value, p)

        return p

    def on_assign(self, node, myparents):
        """
        Assign(expr* targets, expr value)
        """
        if len(node.targets) > 1:
            raise NotImplementedError("Parallel assignments")

        p = [ControlFlowNode(parents=myparents, ast=node)]
        p = self.walk(node.value, p)

        return p

    def on_pass(self, node, myparents):
        return [ControlFlowNode(parents=myparents, ast=node)]

    def on_break(self, node, myparents):
        parent = myparents[0]
        while not hasattr(parent, "exit_nodes"):
            # we have ordered parents
            parent = parent.parents[0]
        assert hasattr(parent, "exit_nodes")
        p = ControlFlowNode(parents=myparents, ast=node)

        # make the break one of the parents of label node.
        parent.exit_nodes.append(p)

        # break doesn"t have immediate children
        return []

    def on_continue(self, node, myparents):
        parent = myparents[0]
        while not hasattr(parent, "exit_nodes"):
            # we have ordered parents
            parent = parent.parents[0]
        assert hasattr(parent, "exit_nodes")
        p = ControlFlowNode(parents=myparents, ast=node)

        # make continue one of the parents of the original test node.
        parent.add_parent(p)

        # return the parent because a continue is not the parent
        # for the just next node
        return []

    def on_for(self, node, myparents):
        # node.target in node.iter: node.body
        # The For loop in python (no else) can be translated
        # as follows:
        # 
        # for a in iterator:
        #      mystatements
        #
        # __iv = iter(iterator)
        # while __iv.__length_hint() > 0:
        #     a = next(__iv)
        #     mystatements
        
        init_node = ControlFlowNode(parents=myparents, ast=ast.parse("__iv = iter(%s)" % astor.to_source(node.iter).strip()).body[0])
        ast.copy_location(init_node.ast_node, node.iter)
        
        _test_node = ControlFlowNode(parents=[init_node], ast=ast.parse("_for: __iv.__length__hint__() > 0").body[0])
        ast.copy_location(_test_node.ast_node, node)

        # we attach the label node here so that break can find it.
        _test_node.exit_nodes = []
        test_node = self.walk(node.iter, [_test_node])

        extract_node = ControlFlowNode(parents=test_node, ast=ast.parse("%s = next(__iv)" % astor.to_source(node.target).strip()).body[0])
        ast.copy_location(extract_node.ast_node, node.iter)

        # now we evaluate the body, one at a time.
        p1 = [extract_node]
        for n in node.body:
            p1 = self.walk(n, p1)

        # the test node is looped back at the end of processing.
        _test_node.add_parents(p1)

        return _test_node.exit_nodes + test_node

    def on_while(self, node, myparents):
        # For a while, the earliest parent is the node.test
        _test_node = ControlFlowNode(parents=myparents, ast=ast.parse("_while: %s" % astor.to_source(node.test).strip()).body[0])
        ast.copy_location(_test_node.ast_node, node.test)
        _test_node.exit_nodes = []
        test_node = self.walk(node.test, [_test_node])

        # we attach the label node here so that break can find it.

        # now we evaluate the body, one at a time.
        p1 = test_node
        for n in node.body:
            p1 = self.walk(n, p1)

        # the test node is looped back at the end of processing.
        _test_node.add_parents(p1)

        # link label node back to the condition.
        return _test_node.exit_nodes + test_node

    def on_if(self, node, myparents):
        _test_node = ControlFlowNode(parents=myparents, ast=ast.parse("_if: %s" % astor.to_source(node.test).strip()).body[0])
        ast.copy_location(_test_node.ast_node, node.test)
        test_node = self.walk(node.test, [_test_node])
        g1 = test_node
        for n in node.body:
            g1 = self.walk(n, g1)
        g2 = test_node
        for n in node.orelse:
            g2 = self.walk(n, g2)
        return g1 + g2

    def on_binop(self, node, myparents):
        left = self.walk(node.left, myparents)
        right = self.walk(node.right, left)
        return right

    def on_compare(self, node, myparents):
        left = self.walk(node.left, myparents)
        right = self.walk(node.comparators[0], left)
        return right

    def on_unaryop(self, node, myparents):
        return self.walk(node.operand, myparents)

    def on_call(self, node, myparents):
        def get_func(node):
            if type(node.func) is ast.Name:
                mid = node.func.id
            elif type(node.func) is ast.Attribute:
                mid = node.func.attr
            elif type(node.func) is ast.Call:
                mid = get_func(node.func)
            elif type(node.func) is ast.BoolOp:
                mid = node.func.op
            else:
                raise Exception(str(type(node.func)))
            return mid
            #mid = node.func.value.id

        p = myparents
        for a in node.args:
            p = self.walk(a, p)
        mid = get_func(node)
        myparents[0].add_calls(mid)

        # these need to be unlinked later if our module actually defines these
        # functions. Otherwsise we may leave them around.
        # during a call, the direct child is not the next
        # statement in text.
        for c in p:
            c.calllink = 0
        return p

    def on_expr(self, node, myparents):
        p = [ControlFlowNode(parents=myparents, ast=node)]
        return self.walk(node.value, p)

    def on_return(self, node, myparents):
        parent = myparents[0][0] if isinstance(myparents, tuple) else myparents[0]

        val_node = self.walk(node.value, myparents)
        # on return look back to the function definition.
        while not hasattr(parent, "return_nodes"):
            parent = parent.parents[0]
        assert hasattr(parent, "return_nodes")

        p = ControlFlowNode(parents=val_node, ast=node)

        # make the break one of the parents of label node.
        parent.return_nodes.append(p)

        # return doesnt have immediate children
        return []

    def on_functiondef(self, node, myparents):
        # a function definition does not actually continue the thread of
        # control flow
        # name, args, body, decorator_list, returns
        fname = node.name
        args = node.args
        returns = node.returns

        enter_node = ControlFlowNode(parents=[], ast=ast.parse("enter: %s(%s)" % (node.name, ", ".join([a.arg for a in node.args.args])) ).body[0]) # sentinel
        enter_node.calleelink = True
        ast.copy_location(enter_node.ast_node, node)
        exit_node = ControlFlowNode(parents=[], ast=ast.parse("exit: %s(%s)" % (node.name, ", ".join([a.arg for a in node.args.args])) ).body[0]) # sentinel
        exit_node.fn_exit_node = True
        ast.copy_location(exit_node.ast_node, node)
        enter_node.return_nodes = []  # sentinel

        p = [enter_node]
        for n in node.body:
            p = self.walk(n, p)

        for n in p:
            if n not in enter_node.return_nodes:
                enter_node.return_nodes.append(n)

        for n in enter_node.return_nodes:
            exit_node.add_parent(n)

        self.functions[fname] = [enter_node, exit_node]
        self.functions_node[enter_node.lineno()] = fname

        return myparents

    def get_defining_function(self, node):
        if node.lineno() in self.functions_node:
            return self.functions_node[node.lineno()]
        if not node.parents:
            self.functions_node[node.lineno()] = ""
            return ""
        val = self.get_defining_function(node.parents[0])
        self.functions_node[node.lineno()] = val
        return val

    def link_functions(self):
        for nid,node in ControlFlowRegistry.cache.items():
            if node.calls:
                for calls in node.calls:
                    if calls in self.functions:
                        enter, exit = self.functions[calls]
                        enter.add_parent(node)
                        if node.children:
                            # # until we link the functions up, the node
                            # # should only have succeeding node in text as
                            # # children.
                            # assert(len(node.children) == 1)
                            # passn = node.children[0]
                            # # We require a single pass statement after every
                            # # call (which means no complex expressions)
                            # assert(type(passn.ast_node) == ast.Pass)

                            # # unlink the call statement
                            assert node.calllink > -1
                            node.calllink += 1
                            for i in node.children:
                                i.add_parent(exit)
                            # passn.set_parents([exit])
                            # ast.copy_location(exit.ast_node, passn.ast_node)

                            # #for c in passn.children: c.add_parent(exit)
                            # #passn.ast_node = exit.ast_node

    def update_functions(self):
        for nid,node in ControlFlowRegistry.cache.items():
            _n = self.get_defining_function(node)

    def update_children(self):
        for nid,node in ControlFlowRegistry.cache.items():
            for p in node.parents:
                p.add_child(node)

    def generate_control_flow(self, src):
        node = self.parse(src)
        nodes = self.walk(node, [self.founder])
        self.last_node = ControlFlowNode(parents=nodes, ast=ast.parse("stop").body[0])
        ast.copy_location(self.last_node.ast_node, self.founder.ast_node)
        self.update_children()
        self.update_functions()
        self.link_functions()


# helper functions

def read_files(file_names):
    source = ""
    fns = [f.strip() for f in file_names.split(",")] if isinstance(file_names, str) else file_names
    for fn in fns:
        with open(fn, "r") as f:
            source += f.read()
    return source


def generate_control_flow(source_code, remove_start_stop=True):
    ControlFlowRegistry.reset()

    control_flow = ControlFlow()
    control_flow.generate_control_flow(source_code)
    cache = dict(ControlFlowRegistry.cache)

    if remove_start_stop:
        return {k:cache[k] for k in cache if cache[k].source() not in {"start", "stop"}}

    return cache


def get_control_flow(file_names):
    control_flow = ControlFlow()
    control_flow.gen_cfg(read_files(file_names))
    cache = ControlFlowRegistry.cache
    g = {}
    for k, v in cache.items():
        j = v.to_json()
        at = j["at"]
        parents_at = [cache[p].to_json()["at"] for p in j["parents"]]
        children_at = [cache[c].to_json()["at"] for c in j["children"]]
        if at not in g:
            g[at] = {"parents": set(), "children": set()}
        # remove dummy nodes
        ps = set([p for p in parents_at if p != at])
        cs = set([c for c in children_at if c != at])
        g[at]["parents"] |= ps
        g[at]["children"] |= cs
        if v.calls:
            g[at]["calls"] = v.calls
        g[at]["function"] = control_flow.functions_node[v.lineno()]
    return (g, control_flow.founder.ast_node.lineno, control_flow.last_node.ast_node.lineno)


def compute_dominator(control_flow, start=0, key="parents"):
    dominator = {}
    dominator[start] = {start}
    all_nodes = set(control_flow.keys())
    rem_nodes = all_nodes - {start}
    for n in rem_nodes:
        dominator[n] = all_nodes

    c = True
    while c:
        c = False
        for n in rem_nodes:
            pred_n = control_flow[n][key]
            doms = [dominator[p] for p in pred_n]
            i = set.intersection(*doms) if doms else set()
            v = {n} | i
            if dominator[n] != v:
                c = True
            dominator[n] = v
    return dominator


def compute_flow(file_names):
    control_flow, first, last = get_control_flow(file_names)
    return control_flow, compute_dominator(
        control_flow, start=first), compute_dominator(
            control_flow, start=last, key="children")


def generate_graph(cache, arcs=[]):
    def unhack(v):
        for i in ["if", "while", "for", "elif"]:
            v = re.sub(r"^_%s:" % i, "%s:" % i, v)
        return v
    colors = {-1: None, 0: "green", 1: "red"}
    kind = {-1: None, 0: "true", 1: "false"}
    graph = pygraphviz.AGraph(strict=False, directed=True)
    cov_lines = set(i for i,j in arcs)
    for nid, cnode in cache.items():
        lineno = cnode.lineno()
        shape, peripheries = "oval", "1"
        if isinstance(cnode.ast_node, ast.AnnAssign):
            if cnode.ast_node.target.id in {"_if", "_for", "_while"}:
                shape = "diamond"
            elif cnode.ast_node.target.id in {"enter", "exit"}:
                shape, peripheries = "oval", "2"
        else:
            shape = "rectangle"

        graph.add_node(cnode.rid, shape=shape, peripheries=peripheries)
        n = graph.get_node(cnode.rid)
        n.attr["label"] = "%d: %s" % (lineno, unhack(cnode.source()))

        for pn in cnode.parents:
            plineno = pn.lineno()
            if hasattr(pn, "calllink") and pn.calllink > 0 and not hasattr(cnode, "calleelink"):
                graph.add_edge(pn.rid, cnode.rid, style="dotted", weight=100)
                continue

            if arcs:
                if  (plineno, lineno) in arcs:
                    graph.add_edge(pn.rid, cnode.rid, color="green")
                elif plineno == lineno and lineno in cov_lines:
                    graph.add_edge(pn.rid, cnode.rid, color="green")
                elif hasattr(cnode, "fn_exit_node") and plineno in cov_lines:  # child is exit and parent is covered
                    graph.add_edge(pn.rid, cnode.rid, color="green")
                elif hasattr(pn, "fn_exit_node") and len(set(n.lineno() for n in pn.parents) | cov_lines) > 0:  # parent is exit and one of its parents is covered.
                    graph.add_edge(pn.rid, cnode.rid, color="green")
                elif plineno in cov_lines and hasattr(cnode, "calleelink"): # child is a callee (has calleelink) and one of the parents is covered.
                    graph.add_edge(pn.rid, cnode.rid, color="green")
                else:
                    graph.add_edge(pn.rid, cnode.rid, color="red")
            else:
                order = {c.rid: rid for rid,c in enumerate(pn.children)}
                if len(order) < 2:
                    graph.add_edge(pn.rid, cnode.rid)
                else:
                    # print(order, pn.rid, "(" + str(pn.lineno()) + ")" + "[" + pn.source() + "]", cnode.rid, "(" + str(cnode.lineno()) + ")" + "[" + cnode.source() + "]", cnode.items())
                    o = order.get(cnode.rid, -1)
                    # print(o)
                    graph.add_edge(pn.rid, cnode.rid, color=colors[o], label=kind[o])
    return graph


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="python files(s) to be parsed (comma separated)")
    parser.add_argument("--output", required=True, help="output file")

    args = parser.parse_args()

    cfg = generate_control_flow(read_files(args.input))
    graph = generate_graph(cfg)
    graph.draw(args.output, prog="dot")
