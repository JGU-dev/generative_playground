import sys
if '/home/ubuntu/shared/GitHub' in sys.path:
    sys.path.remove('/home/ubuntu/shared/GitHub')
try:
    import generative_playground
except:
    import sys, os, inspect

    my_location = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    # sys.path.append('../../../../../..')
    # sys.path.append('../../../../DeepRL')
    # sys.path.append('../../../../../transformer_pytorch')

# from deep_rl import *
# from generative_playground.models.problem.rl.network_heads import CategoricalActorCriticNet
# from generative_playground.train.rl.run_iterations import run_iterations
# from generative_playground.models.problem.rl.DeepRL_wrappers import BodyAdapter, MyA2CAgent
from generative_playground.molecules.model_settings import get_settings
from generative_playground.molecules.train.pg.hypergraph.main_train_policy_gradient_minimal import train_policy_gradient
from generative_playground.molecules.guacamol_utils import guacamol_goal_scoring_functions
from generative_playground.models.temperature_schedule import toothy_exp_schedule, shifted_cosine_schedule, \
    seesaw_exp_schedule
batch_size = 20# 20
drop_rate = 0.5
molecules = True
grammar_cache = 'hyper_grammar_guac_10k_with_clique_collapse.pickle'#'hyper_grammar.pickle'
grammar = 'hypergraph:' + grammar_cache
settings = get_settings(molecules, grammar)
ver = 'v2'
obj_num = 0
reward_funs = guacamol_goal_scoring_functions(ver)
# this accepts a list of SMILES strings
reward_fun = reward_funs[obj_num]
# # later will run this ahead of time
# gi = GrammarInitializer(grammar_cache)


root_name = 'xtest91' + ver + '_' + str(obj_num) + '_lr4e-5'
max_steps = 60
model, gen_fitter, disc_fitter = train_policy_gradient(molecules,
                                                       grammar,
                                                       EPOCHS=100,
                                                       BATCH_SIZE=batch_size,
                                                       reward_fun_on=reward_fun,
                                                       max_steps=max_steps,
                                                       lr_on=0.05, # crazy, to be used with the cosine schedule!
                                                       lr_discrim=0.0,
                                                       # lr_schedule=shifted_cosine_schedule,
                                                       discrim_wt=0.0,
                                                       p_thresh=-10,
                                                       drop_rate=drop_rate,
                                                       reward_sm=0.0,
                                                       decoder_type='graph_conditional',  #'rnn_graph',# 'attention',
                                                       plot_prefix='',
                                                       dashboard=root_name,  # 'policy gradient',
                                                       save_file_root_name=root_name,
                                                       preload_file_root_name=None,#root_name,  #'guacamol_ar_emb_node_rpev2_0lr2e-5',#'guacamol_ar_nodev2_0lr2e-5',#root_name,
                                                       smiles_save_file=root_name.replace(' ', '_') + '_smiles.zip',
                                                       on_policy_loss_type='advantage_record',
                                                       rule_temperature_schedule=toothy_exp_schedule,
                                                       eps=0.0,
                                                       priors='conditional',
                                                       entropy_wgt=1.0)
# preload_file='policy_gradient_run.h5')

while True:
    next(gen_fitter)
    # for _ in range(1):
    #     next(disc_fitter)
