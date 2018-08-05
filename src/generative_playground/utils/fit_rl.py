import torch
from torch.autograd import Variable
from generative_playground.utils.gpu_utils import to_gpu

def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)

def to_variable(x):
    if type(x)==tuple:
        return tuple([to_variable(xi) for xi in x])
    elif 'ndarray'in str(type(x)):
        return to_gpu(torch.from_numpy(x))
    elif 'Variable' not in str(type(x)):
        return Variable(x)
    else:
        return x

# The fit function is a generator, so one can call several of these in
# the sequence one desires
def fit_rl(train_gen = None,
           model = None,
           optimizer = None,
           scheduler = None,
           epochs = None,
           loss_fn = None,
           grad_clip = 5,
           metric_monitor = None,
           checkpointer = None
           ):

    print('setting up fit...')
    print('Number of model parameters:', count_parameters(model))
    model.train()
    loss_fn.train()

    for epoch in range(epochs):
        print('epoch ', epoch)
        if scheduler is not None:
            scheduler.step()
        #for inputs_ in train_gen():
        while True:
            #inputs = to_variable(inputs_)
            outputs = model()#inputs)
            loss = loss_fn(outputs)

            # do the fit step
            optimizer.zero_grad()
            loss.backward()
            if grad_clip is not None:
                nice_params = filter(lambda p: p.requires_grad, model.parameters())
                torch.nn.utils.clip_grad_norm(nice_params, grad_clip)
            optimizer.step()

            # push the metrics out
            this_loss = loss.data.item()
            # do the checkpoint
            if checkpointer is not None:
                avg_loss = checkpointer(this_loss, model)

            if metric_monitor is not None:
                metric_monitor(True,
                               this_loss,
                               loss_fn.metrics if hasattr(loss_fn, 'metrics') else None,
                               outputs)
            yield this_loss


