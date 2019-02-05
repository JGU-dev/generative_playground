# original code taken from https://github.com/episodeyang/visdom_helper, edited to support svg output


from visdom import Visdom
import numpy as np

class Dashboard(Visdom):
    def __init__(self, name, server='http://52.213.134.161'):
        super(Dashboard, self).__init__(server=server)
        self.env = name
        self.plots = {}
        self.plot_data = {}

    def plot(self, name, type, *args, **kwargs):
        if 'opts' not in kwargs:
            kwargs['opts'] = {}
        if 'title' not in kwargs['opts']:
            kwargs['opts']['title'] = name

        if hasattr(self, type):
            if name in self.plots:
                getattr(self, type)(win=self.plots[name], *args, **kwargs)
            else:
                id = getattr(self, type)(*args, **kwargs)
                self.plots[name] = id
        else:
            raise AttributeError('plot type: {} does not exist. Please'
                                 'refer to visdom documentation.'.format(type))

    def append(self, name, type, *args, **kwargs):
        if name in self.plots and type != 'svg':
            self.plot(name, type, *args, update='append', **kwargs)
        else:
            self.plot(name, type, *args, **kwargs)

    def plot_metric_dict(self, metric_dict):
        for title, metric in metric_dict.items():
                self.append(title,
                          metric['type'],
                          **{key:value for key, value in metric.items() if key not in ['type','smooth']})

    def remove(self, name):
        del self.plots[name]

    def clear(self):
        self.plots = {}

if __name__ == '__main__':
    vis = Dashboard('my-dashboard')
    #vis.plot()
    for i in range(3):
        vis.append('training_loss',
               'line',
               X=np.array([i]),
               Y=np.array([i]))