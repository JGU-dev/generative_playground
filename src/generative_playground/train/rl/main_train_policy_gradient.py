import os, inspect
import torch.optim as optim
from torch.optim import lr_scheduler
import torch

from generative_playground.models.losses.vae_loss import VAELoss
from generative_playground.utils.fit_rl import fit_rl
from generative_playground.data_utils.data_sources import DatasetFromHDF5, train_valid_loaders, DuplicateIter
from generative_playground.utils.gpu_utils import use_gpu, to_gpu
from generative_playground.models.model_settings import get_settings, get_model
from generative_playground.utils.metric_monitor import MetricPlotter
from generative_playground.utils.checkpointer import Checkpointer
from generative_playground.models.problem.rl.task import SequenceGenerationTask
from generative_playground.models.model_settings import get_decoder
from generative_playground.models.losses.policy_gradient_loss import PolicyGradientLoss
from generative_playground.models.decoder.policy import SoftmaxRandomSamplePolicy, PolicyFromTarget
from generative_playground.data_utils.data_sources import MultiDatasetFromHDF5, train_valid_loaders, IterableTransform
from generative_playground.data_utils.data_sources import IncrementingHDF5Dataset

def train_policy_gradient(molecules = True,
              grammar = True,
              EPOCHS = None,
              BATCH_SIZE = None,
                          reward_fun=None,
                          max_steps=277,
              lr = 2e-4,
              drop_rate = 0.0,
              plot_ignore_initial = 0,
              save_file = None,
              preload_file = None,
              decoder_type='action',
              plot_prefix = '',
              dashboard = 'policy gradient',
                          smiles_save_file=None,
              preload_weights=False):

    root_location = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    root_location = root_location + '/../'
    save_path = root_location + 'pretrained/' + save_file
    smiles_save_path = root_location + 'pretrained/' + smiles_save_file
    if preload_file is None:
        preload_path = save_path
    else:
        preload_path = root_location + 'pretrained/' + preload_file

    settings = get_settings(molecules=molecules,grammar=grammar)

    if EPOCHS is not None:
        settings['EPOCHS'] = EPOCHS
    if BATCH_SIZE is not None:
        settings['BATCH_SIZE'] = BATCH_SIZE

    save_dataset = IncrementingHDF5Dataset(smiles_save_path)

    task = SequenceGenerationTask(molecules=molecules,
                                  grammar=grammar,
                                  reward_fun=reward_fun,
                                  batch_size=BATCH_SIZE,
                                  max_steps=max_steps,
                                  save_dataset=save_dataset)

    model, _ = get_decoder(molecules,
                           grammar,
                           z_size=settings['z_size'],
                           decoder_hidden_n=200,
                           feature_len=settings['feature_len'],
                           max_seq_length=max_steps,
                           drop_rate=drop_rate,
                           decoder_type=decoder_type,
                           task=task)

    nice_params = filter(lambda p: p.requires_grad, model.parameters())
    optimizer = optim.Adam(nice_params, lr=lr)
    scheduler = lr_scheduler.StepLR(optimizer, step_size=100, gamma=0.99)

    loss_obj = PolicyGradientLoss()

    metric_monitor = MetricPlotter(plot_prefix=plot_prefix,
                                   loss_display_cap=float('inf'),
                                   dashboard_name=dashboard,
                                   plot_ignore_initial=plot_ignore_initial)

    checkpointer = Checkpointer(valid_batches_to_checkpoint=1,
                                save_path=save_path)

    def my_gen():
        for _ in range(1000):
            yield to_gpu(torch.zeros(BATCH_SIZE, settings['z_size']))

    fitter = fit_rl(train_gen=my_gen,
                 model=model,
                 optimizer=optimizer,
                 scheduler=scheduler,
                 epochs=EPOCHS,
                 loss_fn=loss_obj,
                 grad_clip=5,
                 metric_monitor=metric_monitor,
                 checkpointer=checkpointer)

    # get existing molecule data to add training
    main_dataset = DatasetFromHDF5(settings['data_path'], 'actions')

    # TODO change call to a simple DataLoader, no validation
    train_loader, valid_loader = train_valid_loaders(main_dataset,
                                                     valid_fraction=0.1,
                                                     batch_size=BATCH_SIZE,
                                                     pin_memory=use_gpu)


    def optimizer_gen(fitter, data_gen, model):
        while True:
            data_iter = data_gen.__iter__()
            try:
                model.policy = SoftmaxRandomSamplePolicy()
                yield next(fitter)
                x_actions = next(data_iter).to(torch.int64)
                model.policy = PolicyFromTarget(x_actions)
                yield next(fitter)
            except StopIteration:
                data_iter = data_gen.__iter__()

    return model, optimizer_gen(fitter, train_loader, model)

