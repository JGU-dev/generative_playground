import numpy as np
import math
from collections import OrderedDict
from math import floor
from generative_playground.codec.hypergraph_mask_generator import expand_index_to_id, \
    apply_one_action, get_log_conditional_freqs, get_full_logit_priors
from generative_playground.codec.codec import get_codec

num_bins = 20 # TODO: replace with a Value Distribution object
num_actions = 200

def explore(root_node, num_sims):
    for _ in range(num_sims):
        next_node = root_node
        reward = 0
        while True:
            is_terminal = next_node.is_terminal()
            if is_terminal:
                next_node.start_back_up(reward)
                break
            else:
                probs = next_node.action_probabilities()
                action = np.random.multinomial(1,probs)[0]
                next_node, reward = next_node.apply_action(action)

    save_experience_tuples(root_node)

def save_experience_tuples(node):
    pass
    # recursively goes through the trees,
    # updates the experience buffer with all the tuples where self.child_run_count > thresh


# Tree:
# linked tree with nodes
class MCTSNode:
    def __init__(self, grammar, parent, source_action, value_distr):
        """
        Creates a placeholder with just the value distribution guess, to be aggregated by the parent
        :param value_distr:
        """
        self.value_distr_total = value_distr
        self.child_run_count = 1
        self.refresh_prob_thresh = 0.1
        self.decay = 0.99
        self.grammar = grammar
        self.parent = parent
        self.source_action = source_action
        self.action_probs = None
        self.children = [] # maps action index to child
        self.action_ids = []
        self.graph = None

    def is_terminal(self):
        # TODO: replace stub with real implementation
        return np.random.random((1,))[0] < 0.2

    def expand(self):
        if self.parent is not None:
            self.graph = apply_rule(self.parent.graph, self.source_action)
        freqs = get_log_conditional_freqs(self.grammar, [self.graph])
        full_logit_priors, _, node_mask = get_full_logit_priors(self.graph) # TODO: proper arguments
        priors = full_logit_priors + freqs

        for action, valid in enumerate(node_mask[0]):
            if valid: #TODO: use model-predicted value distrs here instead of self
                self.children.append(MCTSNode(self.grammar, self, action, self.value_distr()))
                self.action_ids.append(action)

        self.priors = priors[0][node_mask[0] > 0]
        self.priors = self.priors/self.priors.sum()
        self.refresh_probabilities()

    def value_distr(self):
        return self.value_distr_total/self.child_run_count

    def action_probabilities(self):
        if np.random.random([1][0]) < self.refresh_prob_thresh:
            self.refresh_probabilities()
        tmp = self.action_probs * self.priors
        return tmp/tmp.sum()

    def apply_action(self, action):
        chosen_child = self.children[action]
        if chosen_child.graph is None:
            chosen_child.expand()
        reward = get_reward(chosen_child.graph)
        return chosen_child, reward

    def refresh_probabilities(self):
        # iterate over all children, get their value distrs, calculate Thompson probs
        child_distributions = np.array([child.value_distr() for child in self.children])
        self.action_probs = thompson_probabilities(child_distributions)

    def start_back_up(self, reward=None):
        self.value_distr_total = to_bins(reward, num_bins)
        self.child_run_count=1
        if self.parent is not None:
            self.parent.back_up(self.value_distr())

    def back_up(self, child_value_distr):
        self.value_distr_total *= self.decay
        self.value_distr_total += child_value_distr

        self.child_run_count *= self.decay
        self.child_run_count +=1

        if self.parent is not None:
            self.parent.back_up(self.value_distr())

def to_bins(reward, num_bins): # TODO: replace with a ProbabilityDistribution object
    reward = max(min(reward,1.0), 0.0)
    out = np.zeros([num_bins])
    ind = math.floor(reward*num_bins*0.9999)
    out[ind] = 1
    return out

def thompson_probabilities(x): # TODO: replace stub with real impl
    tmp = np.random.random((x.shape[0],))
    return tmp/tmp.sum()

def get_reward(x): # TODO: replace stub with real impl
    return np.random.random([1])[0]

def apply_rule(graph, action): # TODO: replace stub with real impl
    return [] # proxy for a graph

def get_mask(graph):
    out = np.zeros((num_actions,))
    out[3] = 1
    out[5] = 1
    out[10] = 1
    priors = np.random.random((num_actions,))
    priors = priors/priors.sum()
    return out, priors

def apply_rule(graph, action_index, grammar):
    '''
    Applies a rule to a graph, using the grammar to convert from index to actual rule
    :param graph: a hypergraph
    :param action_index:
    :return:
    '''
    num_actions = len(grammar)
    node_index = [floor(a.item() / num_actions) for a in action_index]
    rule_index = [a.item() % num_actions for a in action_index]
    next_expand_id = expand_index_to_id(graph, node_index)
    new_graph = apply_one_action(graph, rule_index, next_expand_id)
    return new_graph


if __name__=='__main__':
    grammar_cache = 'hyper_grammar_guac_10k_with_clique_collapse.pickle'  # 'hyper_grammar.pickle'
    grammar = 'hypergraph:' + grammar_cache
    max_seq_length = 50
    codec = get_codec(True, grammar, max_seq_length)
    root_node = MCTSNode(codec.grammar, None, None, np.ones((num_bins,))/num_bins)
    root_node.expand()
    explore(root_node, 1000)
    print(root_node.value_distr())
    print("done!")