from __future__ import print_function
import argparse
import time
import os

import numpy as np
import six

import chainer
import chainer.functions as F
import chainer.links as L
from chainer import cuda
from chainer import computational_graph
from chainer import serializers

import mlp as mlp


# Network definition
class MLP(chainer.Chain):

    def __init__(self, n_units, n_out):
        super(MLP, self).__init__(
            # the size of the inputs to each layer will be inferred
            l1=L.Linear(None, n_units),  # n_in -> n_units
            l2=L.Linear(None, n_units),  # n_units -> n_units
            l3=L.Linear(None, n_out),  # n_units -> n_out
        )
        # Define train flag
        self.train = True

    def __call__(self, x, t=None):
        h1 = F.relu(self.l1(x))
        h2 = F.relu(self.l2(h1))
        y = self.l3(h2)
        if self.train:
            # return loss in training phase
            #y = self.predictor(x)
            self.loss = F.softmax_cross_entropy(y, t)
            self.accuracy = F.accuracy(y, t)
            return self.loss
        else:
            # return y in predict/inference phase
            return y


def main():
    parser = argparse.ArgumentParser(description='Chainer example: MNIST')
    parser.add_argument('--initmodel', '-m', default='',
                        help='Initialize the model from given file')
    parser.add_argument('--batchsize', '-b', type=int, default=100,
                        help='Number of images in each mini-batch')
    parser.add_argument('--epoch', '-e', type=int, default=20,
                        help='Number of sweeps over the dataset to train')
    parser.add_argument('--gpu', '-g', type=int, default=-1,
                        help='GPU ID (negative value indicates CPU)')
    parser.add_argument('--out', '-o', default='result/3',
                        help='Directory to output the result')
    parser.add_argument('--resume', '-r', default='',
                        help='Resume the training from snapshot')
    parser.add_argument('--unit', '-u', type=int, default=50,
                        help='Number of units')
    args = parser.parse_args()

    print('GPU: {}'.format(args.gpu))
    print('# unit: {}'.format(args.unit))
    print('# Minibatch-size: {}'.format(args.batchsize))
    print('# epoch: {}'.format(args.epoch))
    print('')

    # Set up a neural network to train
    # Classifier reports softmax cross entropy loss and accuracy at every
    # iteration, which will be used by the PrintReport extension below.
    model = mlp.MLP(args.unit, 10)
    classifier_model = L.Classifier(model)
    if args.gpu >= 0:
        chainer.cuda.get_device(args.gpu).use()  # Make a specified GPU current
        classifier_model.to_gpu()  # Copy the model to the GPU
    xp = np if args.gpu < 0 else cuda.cupy

    # Setup an optimizer
    optimizer = chainer.optimizers.Adam()
    optimizer.setup(classifier_model)

    # Load the MNIST dataset
    train, test = chainer.datasets.get_mnist()

    batchsize = args.batchsize
    n_epoch = args.epoch
    N = len(train)       # training data size
    N_test = len(test)  # test data size

    # Init/Resume
    if args.initmodel:
        print('Load model from', args.initmodel)
        serializers.load_npz(args.initmodel, classifier_model)
    if args.resume:
        print('Load optimizer state from', args.resume)
        serializers.load_npz(args.resume, optimizer)

    if not os.path.exists(args.out):
        os.makedirs(args.out)

    # Learning loop
    for epoch in six.moves.range(1, n_epoch + 1):
        print('epoch', epoch)

        # training
        perm = np.random.permutation(N)
        sum_accuracy = 0
        sum_loss = 0
        start = time.time()
        for i in six.moves.range(0, N, batchsize):
            x = chainer.Variable(xp.asarray(train[perm[i:i + batchsize]][0]))
            t = chainer.Variable(xp.asarray(train[perm[i:i + batchsize]][1]))

            # Pass the loss function (Classifier defines it) and its arguments
            optimizer.update(classifier_model, x, t)

            if epoch == 1 and i == 0:
                with open('{}/graph.dot'.format(args.out), 'w') as o:
                    g = computational_graph.build_computational_graph(
                        (classifier_model.loss,))
                    o.write(g.dump())
                print('graph generated')

            sum_loss += float(classifier_model.loss.data) * len(t.data)
            sum_accuracy += float(classifier_model.accuracy.data) * len(t.data)
        end = time.time()
        elapsed_time = end - start
        throughput = N / elapsed_time
        print('train mean loss={}, accuracy={}, throughput={} images/sec'.format(
            sum_loss / N, sum_accuracy / N, throughput))

        # evaluation
        sum_accuracy = 0
        sum_loss = 0
        for i in six.moves.range(0, N_test, batchsize):
            index = np.asarray(list(range(i, i + batchsize)))
            x = chainer.Variable(xp.asarray(test[index][0]),
                                 volatile='on')
            t = chainer.Variable(xp.asarray(test[index][1]),
                                 volatile='on')
            loss = classifier_model(x, t)
            sum_loss += float(loss.data) * len(t.data)
            sum_accuracy += float(classifier_model.accuracy.data) * len(t.data)

        print('test  mean loss={}, accuracy={}'.format(
            sum_loss / N_test, sum_accuracy / N_test))

    # Save the model and the optimizer
    print('save the model')
    serializers.save_npz('{}/classifier.model'.format(args.out), classifier_model)
    serializers.save_npz('{}/mlp.model'.format(args.out), model)
    print('save the optimizer')
    serializers.save_npz('{}/mlp.state'.format(args.out), optimizer)

if __name__ == '__main__':
    main()

