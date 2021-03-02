import torch
import pdb
from torch.utils.data import Dataset
from torch.utils.data import TensorDataset, DataLoader

import torchvision
from torchvision import transforms

import numpy as np

from torch.nn import functional as F
import losses

DATA_PATH = './data'

class SiameseDataset(Dataset):
    def __init__(self, ds, n_classes):
        self.dataset = ds
        self.total_data = len(ds)

        if hasattr(ds, 'train_labels'):
            self.labels = ds.train_labels.numpy()
        else:
            self.labels = ds.test_labels.numpy()

        classes = list(range(n_classes))
        self.label_to_indice = {}

        for i in classes:
            pos_indices = np.argwhere(self.labels == i).reshape(-1)
            neg_indices = np.argwhere(self.labels != i).reshape(-1)

            self.label_to_indice[i] = (neg_indices, pos_indices)

    def __getitem__(self, index):
        x, y = self.dataset[index]

        target = np.random.randint(0, 2)
        y_np = int(y.detach().numpy())

        sample_idx = np.random.choice(self.label_to_indice[y_np][target])

        x_sample, _ = self.dataset[sample_idx]

        return x, x_sample, torch.tensor(target).type(torch.FloatTensor)

    def __len__(self):
        return self.total_data


class TripetLossDataset(Dataset):
    def __init__(self, ds):
        self.dataset = ds
        self.total_data = len(ds)

        if hasattr(ds, 'train_labels'):
            self.labels = ds.train_labels.numpy()
        else:
            self.labels = ds.test_labels.numpy()

        classes = list(range(10))
        self.label_to_indice = {}

        for i in classes:
            pos_indices = np.argwhere(self.labels == i).reshape(-1)
            neg_indices = np.argwhere(self.labels != i).reshape(-1)

            self.label_to_indice[i] = (neg_indices, pos_indices)

    def __getitem__(self, index):
        x, y = self.dataset[index]

        y_np = int(y.detach().numpy())

        pos_idx = np.random.choice(self.label_to_indice[y_np][1])
        neg_idx = np.random.choice(self.label_to_indice[y_np][0])

        pos_x, _ = self.dataset[pos_idx]
        neg_x, _ = self.dataset[neg_idx]

        return x, pos_x, neg_x

    def __len__(self):
        return self.total_data


def get_dataset(loss, name, batch_size=32, args = None):
    data_path = '%s/%s' % (DATA_PATH, name)
    print(data_path)

    if name == 'XRD':
        train_x = np.load(args.train_path + '/x.npy')
        train_y = np.load(args.train_path + '/y.npy')
        test_x = np.load(args.test_path + '/x.npy')
        test_y = np.load(args.test_path + '/y.npy')


        tensor_x = torch.Tensor(train_x)[:, None, :] # transform to torch tensor
        tensor_y = torch.Tensor(train_y).squeeze()
        trainset = TensorDataset(tensor_x,tensor_y) # create your datset
        trainset.train_labels = tensor_y
    
        tensor_x = torch.Tensor(test_x)[:, None, :] # transform to torch tensor
        tensor_y = torch.Tensor(test_y).squeeze()
        testset = TensorDataset(tensor_x,tensor_y) # create your datset
        testset.train_labels = tensor_y


    else:
        tds = getattr(torchvision.datasets, name)

        trainset = tds(root=data_path, train=True, download=True, transform=transforms.ToTensor())
        testset = tds(root=data_path, train=False, download=True, transform=transforms.ToTensor())

    trainloader = torch.utils.data.DataLoader(trainset, batch_size=batch_size, shuffle=True, num_workers=1)
    testloader = torch.utils.data.DataLoader(testset, batch_size=batch_size, shuffle=False, num_workers=1)

    if loss is losses.contastive_loss or loss is losses.binary_cross_entropy:
        siamese_train_loader = torch.utils.data.DataLoader(SiameseDataset(trainset, n_classes = args.n_classes), batch_size=batch_size,
                                                           shuffle=True,
                                                           num_workers=1)

        siamese_test_loader = torch.utils.data.DataLoader(SiameseDataset(trainset, n_classes = args.n_classes), batch_size=batch_size,
                                                          shuffle=False,
                                                          num_workers=1)

        return siamese_train_loader, siamese_test_loader, trainloader, testloader
    elif loss is losses.tripet_loss:
        tp_train_loader = torch.utils.data.DataLoader(TripetLossDataset(trainset), batch_size=batch_size, shuffle=True,
                                                      num_workers=1)

        tp_test_loader = torch.utils.data.DataLoader(TripetLossDataset(testset), batch_size=batch_size,
                                                     shuffle=False,
                                                     num_workers=1)
        return tp_train_loader, tp_test_loader, trainloader, testloader
    elif loss is F.nll_loss:
        return trainloader, testloader, trainloader, testloader

    raise SystemError('no %s dataset available for %s' % (name, loss))
