import copy
import frozendict
import networkx as nx
import uuid
from rdkit import Chem
from rdkit.Chem import MolFromSmiles, AddHs, MolToSmiles, RemoveHs, Kekulize, BondType
import pickle
from functools import lru_cache

from collections import OrderedDict


strict_validation = False

bond_types =[]
# each edge is a FrozenDict with a random ID
# each node is an OrderedDict with value 'edges' containing a list of edges, and optional other values from rdkit, and has a random ID too
class Node:
    def __init__(self, edge_ids=[],
                 edges=None,
                 graph=None,
                 is_terminal=False,
                 data={}):
        self.edge_ids = edge_ids
        self.data = data
        self.is_terminal = is_terminal
        # the below two properties are set to nonnegative values in the graphs that are rules in a grammar, or generated from these
        self.rule_id = -1
        self.rule_index = -1

        if graph is not None:
            edges = [graph.edges[edge_id] for edge_id in edge_ids]
        if edges is None:
            edges = [None] * len(edge_ids)
        assert len(edges) == len(edge_ids), "Number of edge IDs must equal number of edges"
        self.edges = edges

    def __str__(self):
        return ':'.join([str(edge.type) for edge in self.edges]) + ' ' + \
               ('t:' if self.is_terminal else 'nt:') + str(self.data)

    def __eq__(self, other):
        return self.__str__() == other.__str__()

    def __hash__(self):
        return hash(self.__str__())

    def conditioning_tuple(self):
        return (self.rule_id, self.node_index) # nonterminal index in the original rule



class Edge:
    def __init__(self, type, data={}):
        self.type = type
        self.data = data


class HypergraphTree(list):
    def __init__(self, node=None, children=None):
        children = children or []
        self.node = node  # hypergraph
        super().__init__(children)
        self.validate()

    def validate(self):
        assert len(self) == len(self.node.child_ids()), "Mismatched self length ({}) with child_ids ({})".format(len(self), len(self.node.child_ids()))
        for (child_id, subtree) in zip(self.node.child_ids(), self):
            assert str(self.node.node[child_id]) == str(subtree.node.parent_node()), "Mismatch between node nonterminals and subtree parent nodes"

    def size(self):
        return 1 + sum([child.size() for child in self])

    def rules(self):
        return graph_tree_to_rules_list(self)



def graph_tree_to_rules_list(tree):
    assert isinstance(tree, HypergraphTree)
    rules_list = [tree.node]
    for child in reversed(tree): # need to reverse to get correct expansion order
        rules_list += graph_tree_to_rules_list(child)
    return rules_list


class HyperGraph:
    def __init__(self):
        self.node = OrderedDict()  # of Nodes
        self.edges = OrderedDict() # of edges
        self.parent_node_id = None  # The node we'll match/merge when expanding
        self._child_ids = None # cached for performance only
        self._nonterminal_ids = None# cached for performance only
        self._node_ids_by_edge_id = None # cached for performance only
        # self.pickled = None

    def shallow_copy(self):
        out = HyperGraph()
        out.node = copy.copy(self.node)
        out.edges = copy.copy(self.edges)
        out.parent_node_id = self.parent_node_id
        return out

    def reorder(self, mapping):
        assert len(mapping) == len(self.node), "Invalid mapping length"
        node_list = list(self.node.items())
        new_node_list = [node_list[ind] for ind in mapping]
        out = HyperGraph()
        out.node = OrderedDict(new_node_list)
        out.edges = self.edges
        out.parent_node_id = self.parent_node_id
        out.validate()
        return out

    # def __getstate__(self):
    #     if self.pickled is not None:
    #         return self.pickled
    #     else:
    #         return pickle.dumps(self.__dict__)
    #
    # def __setstate__(self, state):
    #     if type(state) != dict:
    #         pkl = state
    #         state = pickle.loads(state)
    #     else:
    #         pkl = None
    #     self.__dict__ = state
    #     self.pickled = pkl
    #
    # def __setattr__(self, key, value):
    #     self.__dict__['pickled'] = None
    #     self.__dict__[key] = value

    def clone(self): #create a copy of self that uses different uuids
        clone = HyperGraph()
        clone.add_edges(self.edges.values())
        edge_id_map = {old: new for old, new in zip(self.edges.keys(), clone.edges.keys())}
        for node_id, node in self.node.items():
            new_node = Node(edge_ids=[edge_id_map[old_edge_id] for old_edge_id in node.edge_ids],
                            graph=clone,
                            is_terminal=node.is_terminal,
                            data=node.data)
            if hasattr(node, 'rule_id'):
                new_node.rule_id = node.rule_id
            if hasattr(node, 'node_index'):
                new_node.node_index = node.node_index
            if node_id == self.parent_node_id:
                clone.add_parent_node(new_node)
            else:
                clone.add_node(new_node)

        clone.validate()
        return clone

    def parent_node(self):
        if self.parent_node_id is None:
            return None
        else:
            return self.node[self.parent_node_id]

    def add_edge(self, x: Edge):
        assert isinstance(x, Edge)
        assert x not in list(self.edges.values())
        edge_id = uuid.uuid4()
        self.edges[edge_id] = x
        return edge_id

    def __str__(self):
        out = str(len(self.edges)) + ' edges,'
        for node_id, node in self.node.items():
            if node_id != self.parent_node_id:
                out += ';' + str(node)
        return out

    def __eq__(self, other):
        return hypergraphs_are_equivalent(self, other) is not None

    def __hash__(self):
        return hash(self.__str__())

    def add_edges(self, edges):
        for x in edges:
            self.add_edge(x)

    def add_node(self, x: Node):
        assert isinstance(x, Node)
        self.node[uuid.uuid4()] = x

    def add_parent_node(self, x: Node):
        assert self.parent_node_id is None
        assert isinstance(x, Node)
        self.parent_node_id = uuid.uuid4()
        self.node[self.parent_node_id] = x

    def nonterminal_ids(self):
        if not hasattr(self, '_nonterminal_ids') or self._nonterminal_ids is None:
            self._nonterminal_ids = [key for key, value in self.node.items() if value.is_terminal is False]
        return self._nonterminal_ids


    def terminal_ids(self):
        return [key for key, value in self.node.items() if value.is_terminal is True]

    def child_ids(self):
        if not hasattr(self, '_child_ids') or self._child_ids is None:
            self._child_ids = [key for key in self.nonterminal_ids() if key != self.parent_node_id]
        return self._child_ids

    def child_indices(self):
        return [i for i, id in enumerate(self.node.keys()) if id in self.child_ids()]

    def id_to_index(self, id):
        out = [i for i, id_candidate in enumerate(self.node.keys()) if id_candidate==id]
        assert len(out) == 1, "This id does not exist"
        return out[0]

    def index_to_id(self, idx):
        assert idx < len(self.node), "Index exceeds number of nodes"
        out = [id_candidate for i, id_candidate in enumerate(self.node.keys()) if i == idx]
        return out[0]

    def children(self):
        return [self.node[child_id] for child_id in self.child_ids()]

    def is_parent_node(self, x):
        if self.parent_node_id is None:
            return False
        return self.node[self.parent_node_id] is x

    def __len__(self):
        return len(self.node)

    def node_ids_by_edge_id(self):
        if self._node_ids_by_edge_id is None:
            self._node_ids_by_edge_id = OrderedDict()
            for node_id, node in self.node.items():
                for edge_id in node.edge_ids:
                    if edge_id not in self._node_ids_by_edge_id:
                        self._node_ids_by_edge_id[edge_id] = []
                    self._node_ids_by_edge_id[edge_id].append(node_id)

        return self._node_ids_by_edge_id

    def node_ids_from_edge_id(self, edge_id):
        return self.node_ids_by_edge_id()[edge_id]
        # my_nodes=[]
        # for node_id, node in self.node.items():
        #     if edge_id in node.edge_ids:
        #         my_nodes.append(node_id)
        # return my_nodes

    def validate(self):
        if not strict_validation:
            return
        edge_count = self.node_ids_by_edge_id()
        # edge_count = {}
        # edge_lists = [node.edge_ids for node in self.node.values()]
        # for node in edge_lists:
        #     for edge_id in node:
        #         if edge_id not in edge_count:
        #             edge_count[edge_id] = 1
        #         else:
        #             edge_count[edge_id] += 1
        #
        # for count in edge_count.values():
        #     assert count == 2
        for nodes in edge_count.values():
            assert len(nodes) == 2, "Graph is not 2-regular. Found edge connecting {} nodes".format(len(nodes))

        assert set(edge_count.keys()) == set(self.edges.keys())

    def to_nx(self):
        # create a networkx Graph from self, ignoring any open edges
        # the main information that gets lost hereby is the ordering, so stereochemistry
        # self.check_validity()
        # assert len(self.open_edges) == 0
        G = nx.Graph()
        for n, (node_id, node) in enumerate(self.node.items()):
            G.add_node(node_id, node = node, index=n)

        for edge_id, edge in self.edges.items():
            first, second = self.node_ids_from_edge_id(edge_id)
            G.add_edge(first, second, id=edge_id, data=edge)
        return G

    def other_end_of_edge(self, node_id, edge_id):
        assert edge_id in self.node[node_id].edge_ids
        for other_node_id, other_node in self.node.items():
            if other_node_id != node_id and edge_id in other_node.edge_ids:
                return other_node_id
        raise ValueError("This edge appears to belong to no other node")

    def neighbor_ids(self, node_id):
        n_ids = []
        for edge_id in self.node[node_id].edge_ids:
            n_ids += [x for x in self.node_ids_from_edge_id(edge_id) if x != node_id]
        return n_ids


    # TODO: redo this so it also works when self has open edges, possibly with lhs_node - or does this work already?
    def replace_node(self, lhs_node, graph):
        assert lhs_node['edges'] == len(graph.open_edges)
        self.node = [node_ for node_ in self.node if node_ != lhs_node]
        edge_map = {old_edge: new_edge for old_edge, new_edge in zip(graph.open_edges, lhs_node['edges'])}
        for node_ in graph.nodes:
            new_node = copy.copy(node_)
            # any open edges are mapped to the edges the removed node had
            new_node['edges'] = [edge_map[edge] if edge in edge_map else edge for edge in node_['edges']]
            self.node.append(new_node)

    def to_mol(self):
        return to_mol(self)

    def to_smiles(self):
        return MolToSmiles(self.to_mol())

    @classmethod
    def from_smiles(cls, smiles):
        mol = MolFromSmiles(smiles)
        return cls.from_mol(mol)

    @classmethod
    def from_mol(Class, mol):
        # make the Hs explicit, kekulize, so the graph is easier to work with
        Kekulize(mol, clearAromaticFlags=True)
        #AddHs(mol)

        self = Class()
        # we'll use rdkit's indices as IDs for both nodes and edges

        for bond in mol.GetBonds():
            assert bond.GetIdx() not in self.edges
            bond_type = bond.GetBondType()
            assert bond_type != BondType.AROMATIC
            if bond_type not in bond_types:
                bond_types.append(bond_type)
                print(bond_type)
            this_bond = Edge(type=bond.GetBondType(),
                             data=bond_to_properties(bond))
            self.edges[bond.GetIdx()] = this_bond

        for atom in mol.GetAtoms():
            assert atom.GetIdx() not in self.node
            this_node_edge_ids = [bond.GetIdx() for bond in atom.GetBonds()]
            this_node = Node(edge_ids=this_node_edge_ids,
                             edges=[self.edges[edge_id] for edge_id in this_node_edge_ids],
                             data=atom_to_properties(atom),
                             is_terminal=True)
            self.node[atom.GetIdx()] = this_node



        return self



    @classmethod
    def from_tree_node(Class, mol, tree_node):
        '''
        Constructs a graph from a junction tree node, with nonterminals for parent and children
        :param tree_node:
        :return:
        '''
        '''

        Add a 'parent' node, store its index
        Add child nodes from ['children'].keys()
        add all edges just as they are
        make sure to generate uids for nodes and edges as we create them
        '''
        self = Class()

        atom_id_map = OrderedDict()
        bond_id_map = OrderedDict()
        atoms_to_bonds = OrderedDict()
        for bond_old_id, bond_atoms in tree_node['bonds'].items():
            bond_id = uuid.uuid4()
            assert bond_id not in self.edges
            bond_id_map[bond_old_id] = bond_id
            bond = mol.GetBonds()[bond_old_id]
            for old_atom_id in bond_atoms:
                if old_atom_id not in atom_id_map:
                    atom_id_map[old_atom_id] = uuid.uuid4()
                if atom_id_map[old_atom_id] not in atoms_to_bonds:
                    atoms_to_bonds[atom_id_map[old_atom_id]] = []
                atoms_to_bonds[atom_id_map[old_atom_id]].append(bond_id)

            this_bond = Edge(type=bond.GetBondType(),
                             data=bond_to_properties(bond))
            self.edges[bond_id] = this_bond

        for old_atom_id, new_atom_id in atom_id_map.items():
            if old_atom_id in tree_node['atoms']:
                atom_properties = atom_to_properties(mol.GetAtoms()[old_atom_id])
                this_node = Node(edge_ids=atoms_to_bonds[new_atom_id],
                                 edges=[self.edges[edge_id] for edge_id in atoms_to_bonds[new_atom_id]],
                                 data=atom_properties,
                                 is_terminal=True)
                self.node[new_atom_id] = this_node

        # now create the nonterminal nodes from bunches of loose bonds
        def create_node_from_bondlist(bond_list): # create a node from a bunch of loose bonds
            if len(bond_list):
                new_node_id = uuid.uuid4()
                my_edges = []
                for old_bond_id in bond_list:
                    my_edges.append(bond_id_map[old_bond_id])
                    for x in tree_node['bonds'][old_bond_id]:
                        # remove the atom placeholders created when we created the edges
                        if x not in tree_node['atoms']:
                            if atom_id_map[x] in atoms_to_bonds:
                                del atoms_to_bonds[atom_id_map[x]]

                new_node = Node(edge_ids=my_edges,
                                edges=[self.edges[edge_id] for edge_id in my_edges],
                                is_terminal=False)
                self.node[new_node_id] = new_node
                return new_node_id
            else:
                return None

        self.parent_node_id = create_node_from_bondlist(tree_node['parent_bonds'].keys())
        if 'children' in tree_node:
            for child_group in tree_node['children'].keys():
                create_node_from_bondlist(child_group)

        if self.parent_node_id is not None:
            assert self.parent_node_id in self.node

        self.validate()

        return self

    @classmethod
    def from_graph_tree(Class, tree: HypergraphTree):
        return graph_from_graph_tree(tree)


def bond_to_properties(bond):
    this_bond_data = {'direction': bond.GetBondDir(),
                      'stereo': bond.GetStereo()}
    return this_bond_data


def properties_to_bond(mol, atoms, bond_type, props):
    mol.AddBond(atoms[0], atoms[1], bond_type)  # sadly this doesn't return the index of the new bond
    for bond in mol.GetBonds():
        if bond.GetBeginAtomIdx() == atoms[0] and bond.GetEndAtomIdx() == atoms[1]:
            break
    if 'stereo' in props:
        bond.SetStereo(props['stereo'])
    if 'direction' in props:
        bond.SetBondDir(props['direction'])
    return bond

def graph_from_graph_tree(tree):
    assert isinstance(tree, HypergraphTree)
    this_node = tree.node
    child_nodes = [graph_from_graph_tree(x) for x in tree]
    # as we're recursively reconstructing
    for child_node in child_nodes:
        check_validity(child_node)

    child_ids = this_node.child_ids()
    assert len(child_ids) == len(child_nodes)
    for id, new_node in zip(child_ids, child_nodes):
        this_node = replace_nonterminal(this_node, id, new_node)

    check_validity(this_node)
    this_node.validate()
    return this_node

def check_validity(child_node):
    for node_id, node in child_node.node.items():
        assert node_id == child_node.parent_node_id or len(node.data) > 0

def atom_to_properties(atom):
    this_node_data = {'atomic_num': atom.GetAtomicNum(),
                      'formal_charge': atom.GetFormalCharge(),
                      'chiral_tag': atom.GetChiralTag(),
                      # 'hybridization': atom.GetHybridization(),
                      # 'num_explicit_hs': atom.GetNumExplicitHs(),
                      # 'is_aromatic':atom.GetIsAromatic(),
                      }
    return this_node_data

def atom_from_properties(props):
    a = Chem.Atom(props['atomic_num'])
    a.SetChiralTag(props['chiral_tag'])
    a.SetFormalCharge(props['formal_charge'])
    # a.SetIsAromatic(node['is_aromatic'])
    # a.SetHybridization(node['hybridization'])
    # a.SetNumExplicitHs(node['num_explicit_hs'])
    return a
import rdkit
rdkit.Chem.rdchem.Bond
def to_mol(graph):
    '''
    Creates an rdkit Molecule object from either a HyperGraphFragment, or a networkx graph exported from it
    :param graph:
    :return:
    '''
    mol = Chem.RWMol()
    node_to_idx = {}
    for node_id, node in graph.node.items():
        if 'dict' in str(type(node)).lower():
            node = node['node']
        a = atom_from_properties(node.data)
        idx = mol.AddAtom(a)
        node_to_idx[node_id] = idx

    edges_added = []
    for edge_id, edge in graph.edges.items():
        if type(edge_id) == tuple:  # nx.Graph, edge uniquely identified by vertices
            atom_ids = edge_id
            edge = edge['data']
        else:  # HyperGraphFragment, edge has own id
            atom_ids = graph.node_ids_from_edge_id(edge_id)
        if atom_ids[0] not in graph.node or atom_ids[1] not in graph.node:
            continue  # ignore loose edges, if any
        # try: # TODO: properly check whether a bond already exists
        my_atoms = [node_to_idx[x] for x in atom_ids]
        if my_atoms not in edges_added:
            edges_added.append(my_atoms)
            bond = properties_to_bond(mol,
                                      atoms=my_atoms,
                                      bond_type=edge.type,
                                      props=edge.data)

    # RemoveHs(mol)

    Chem.SanitizeMol(mol)
    return mol


# if __name__ == '__main__':
#     import rdkit
#
#     # TODO: move the below to unit tests!
#     smiles = '[CH2+][C@H](O)c1ccccc1\C(F)=C([Br])\C=C'  # 'O=C=O'
#     smiles = MolToSmiles(MolFromSmiles(smiles))
#     print(smiles)
#     mol = MolFromSmiles(smiles)
#     hg = HyperGraphFragment.from_mol(mol)
#     re_mol = to_mol(hg)
#     re_smiles = MolToSmiles(re_mol)
#     print(re_smiles)
#
#     graph = hg.to_nx()
#     print(MolToSmiles(RemoveHs(to_mol(graph))))
#     print('done!')


def replace_nonterminal(orig_node, loc, new_node):
    orig_node = orig_node.shallow_copy()
    new_node = new_node.clone()
    orig_node.validate()
    new_node.validate()
    node_to_replace = orig_node.node[loc]
    new_root_node = new_node.parent_node()
    assert len(node_to_replace.edge_ids) == len(new_root_node.edge_ids)
    for edge1_id, edge2_id in zip(node_to_replace.edge_ids, new_root_node.edge_ids):
        edge1 = orig_node.edges[edge1_id]
        edge2 = new_node.edges[edge2_id]
        assert edge1.type == edge2.type
        # merge the edges in a somewhat naive fashion
        new_edge = Edge(type=edge1.type, data={**edge1.data, **edge2.data})
        orig_node.edges[edge1_id] = new_edge
        del new_node.edges[edge2_id]
        # in the new segment, replace the edges leading to the root node with edges from the parent
        for node in new_node.node.values():
            for i in range(len(node.edge_ids)):
                if node.edge_ids[i] == edge2_id:
                    node.edge_ids[i] = edge1_id
                    node.edges[i] = new_edge

        # in the old segment, update the edge object corresponding to the unchanged ID:
        for node in orig_node.node.values():
            for i in range(len(node.edge_ids)):
                if node.edge_ids[i] == edge1_id:
                    node.edges[i] = new_edge

    orig_node.edges.update(new_node.edges)
    del new_node.node[new_node.parent_node_id]
    del orig_node.node[loc]
    orig_node.node.update(new_node.node)
    orig_node.validate()
    return orig_node


def hypergraphs_are_equivalent(graph1, graph2, isomorphy=True):
    if graph1 is None or graph2 is None:
        return None
    graph1 = put_parent_node_first(graph1)
    graph2 = put_parent_node_first(graph2)
    if len(graph1) != len(graph2):
        return None

    # index_cache_1 = {}
    # index_cache_2 = {}
    if not isomorphy:
        # node type must match as well as node ordering, nx is just needed to check that the edges also align
        edge2nodes1 = graph1.node_ids_by_edge_id()
        edge2nodes2 = graph2.node_ids_by_edge_id()

        def other_node1(node_id, edge_id):
            nodes = edge2nodes1[edge_id]
            tmp = [n for n in nodes if n != node_id]
            assert len(tmp) == 1, "This node is not connected to this edge!"
            return tmp[0]

        def other_node2(node_id, edge_id):
            nodes = edge2nodes2[edge_id]
            tmp = [n for n in nodes if n != node_id]
            assert len(tmp) == 1, "This node is not connected to this edge!"
            return tmp[0]

        mapping = {id1: id2 for id1, id2 in zip(graph1.node.keys(), graph2.node.keys())}

        for i, (node1_id, node1), (node2_id, node2) in zip(range(len(graph1)), graph1.node.items(), graph2.node.items()):
            if not (graph1.is_parent_node(node1) == graph2.is_parent_node(node2)):
                return None
            elif str(node1) != str(node2) or len(node1.edges) != len(node2.edges):
                return None
            else:
                for edge1_id, edge2_id in zip(node1.edge_ids, node2.edge_ids):
                    edge1 = graph1.edges[edge1_id]
                    edge2 = graph2.edges[edge2_id]
                    if edge1.type != edge2.type or edge1.data != edge2.data:
                        return None
                    # now test that matching edges lead to matching nodes
                    candidate_node_id1 = other_node1(node1_id, edge1_id)
                    candidate_node_id2 = other_node2(node2_id, edge2_id)
                    if mapping[candidate_node_id1] != candidate_node_id2:
                        return None

        return mapping

    else:
        def nodes_match(node1, node2):
            # parent nodes must be aligned
            if not graph1.is_parent_node(node1['node']) == graph2.is_parent_node(node2['node']):
                return False
            # and for all nodes the content must match as well as the ordering
            return str(node1['node']) == str(node2['node'])

        def edges_match(edge1, edge2):
            return edge1['data'].type == edge2['data'].type and edge1['data'].data == edge2['data'].data

        from networkx.algorithms.isomorphism import GraphMatcher
        graph1_nx = graph1.to_nx()
        graph2_nx = graph2.to_nx()
        GM = GraphMatcher(graph1_nx, graph2_nx, edge_match=edges_match, node_match=nodes_match)

        if GM.is_isomorphic():
            # assert str(graph1) == str(graph2)
            # for id1, id2
            # test = {id1: id2 for id1, id2 in zip(graph1.node.keys(), graph2.node.keys())}
            # for id1 in test:
            #     if test[id1] != GM.mapping[id1]:
            #         print("what?")
            assert graph1.parent_node_id is None or GM.mapping[graph1.parent_node_id] == graph2.parent_node_id
            return GM.mapping
        else:
            return None

def put_parent_node_first(rule):
    if rule.parent_node_id is not None:
        new_node_order = [(rule.parent_node_id, rule.parent_node())] + \
            [item for item in rule.node.items() if item[0] != rule.parent_node_id]
        rule.node = OrderedDict(new_node_order)
    return rule

def conditoning_tuple(graph, node_id):
    if graph is None:
        assert node_id is None
        return None, None
    else:
        return graph.node[node_id].conditioning_tuple()


def expand_index_to_id(graph, expand_index=None):
    '''

    :param graph: HyperGraph or None for the first step
    :param expand_index: None or an index of the node in graph.node that we want to expand next
    :return: id of the next node to expand, or None if we have nothing left to expand
    '''
    if graph is None:
        return None # expand_id will be ignored as we'll be starting a new graph

    nonterminals_left = graph.nonterminal_ids()
    if len(nonterminals_left):
        if expand_index is None:
            expand_id = nonterminals_left[-1]
        else:
            expand_id = list(graph.node.keys())[expand_index]
            assert expand_id in nonterminals_left, \
                "The proposed expand location is not valid"
    else:
        expand_id = None
    return expand_id