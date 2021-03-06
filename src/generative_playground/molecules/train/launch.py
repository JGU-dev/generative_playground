from generative_playground.utils.batch_run import batch_run
import os

here = os.path.realpath(__file__)
ohio = False  # True
file = 'hyper_worker'#'genetic'#  #'mcts_local'#
source_root = "/home/ubuntu/shared/GitHub/generative_playground/src"
train_root = source_root + "/generative_playground/molecules/train"

if file == 'conditional':
    python_file = '{}/pg/conditional/v2/train_conditional_v2_parametrized.py'.format(train_root)
elif file == 'mcts_global':
    python_file = '{}/mcts/run_global_model_mcts.py'.format(train_root)
elif file == 'mcts_local':
    python_file = '{}/mcts/run_local_model_mcts.py'.format(train_root)
elif file == 'mcts_mixed':
    python_file = '{}/mcts/run_mixed_model_mcts.py'.format(train_root)
elif file == 'mcts_thompson':
    python_file = '{}/mcts/run_thompson_model_mcts.py'.format(train_root)
elif file == 'genetic':
    python_file = '{}/genetic/genetic_train.py'.format(train_root)
elif file == 'genetic_scan':
    python_file = '{}/genetic/genetic_initial_scan.py'.format(train_root)
elif file == 'hyper_worker':
    python_file = '{}/generative_playground/models/hyperopt/worker.py'.format(source_root)

if ohio:
    key_file = os.path.realpath("../../../../../aws_ohio.pem")
else:
    key_file = os.path.realpath("../../../../../aws_second_key_pair.pem")

ips = ['34.250.50.229']

# workers_per_machine = 3
# job_assignments = {ip: ['--attempt ' + str(i + workers_per_machine*(iip)) + ' --entropy_wgt 0.0 --lr 0.03 ' + '16'
#                         for i in range(workers_per_machine)] for iip, ip in enumerate(ips)}

job_assignments = {'34.250.50.229': ['--db_name HyperTest']}

batch_run(source_root, python_file, key_file, job_assignments, respawner=True)

# screen -ls
# screen -r ...
# ^a dtop



job_assignments = {}
ips = []  # ['34.242.215.15']

# for i, ip in enumerate(ips):
#     job_assignments[ip] = [4*i+j for j in range(4)]
#
# redo = [0]
# job_assignments = {key: [v for v in value if v in redo] for key, value in job_assignments.items()}
# job_assignments = {key: value for key, value in job_assignments.items() if value }
# job_assignments = {'3.15.182.107': [0]}
# lrs = ['0.05', '0.05', '0.1', '0.1']
# ews = ['3.0', '10.0', '3.0', '10.0']
#
# job_assignments = {ip:[] for ip in ips}
# for i in range(74, 4 * 20):
#     attempt = i % 4
#     obj = int(i / 4)
#     ip_ind = int(obj / 4)
#     job_assignments[ips[ip_ind]].append('--attempt ' + str(attempt)
#                                     + ' --lr ' + lrs[0]
#                                     + ' --entropy_wgt ' + ews[0]
#                                     + ' ' + str(obj))


