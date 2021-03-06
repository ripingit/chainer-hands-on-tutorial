"""Inference/predict code for MNIST

model must be trained before inference, train_mnist_4_trainer.py must be executed beforehand.
"""
from __future__ import print_function
import argparse
import time

import numpy as np
import six
import matplotlib.pyplot as plt

import chainer
import chainer.functions as F
import chainer.links as L
from chainer import Chain, Variable, optimizers, serializers
from chainer import datasets, training, cuda, computational_graph


import src.mnist.mlp as mlp


def main():
    parser = argparse.ArgumentParser(description='Chainer example: MNIST')
    parser.add_argument('--modelpath', '-m', default='result/4/mlp.model',
                        help='Model path to be loaded')
    parser.add_argument('--gpu', '-g', type=int, default=-1,
                        help='GPU ID (negative value indicates CPU)')
    parser.add_argument('--unit', '-u', type=int, default=50,
                        help='Number of units')
    args = parser.parse_args()

    # Load the MNIST dataset
    train, test = chainer.datasets.get_mnist()

    # Load trained model
    model = mlp.MLP(args.unit, 10)
    if args.gpu >= 0:
        chainer.cuda.get_device(args.gpu).use()  # Make a specified GPU current
        model.to_gpu()  # Copy the model to the GPU
    xp = np if args.gpu < 0 else cuda.cupy

    serializers.load_npz(args.modelpath, model)

    # check all the results
    wrong_count = 0
    for i in range(len(test)):
        x = Variable(xp.asarray([test[i][0]]))    # test data
        # t = Variable(xp.asarray([test[i][1]]))  # labels
        y = model(x)                              # Inference result
        prediction = y.data.argmax(axis=1)
        if prediction != test[i][1]:
            #print('{}-th data inference is wrong, prediction = {}, actual = {}'
            #      .format(i, prediction, test[i][1]))
            wrong_count += 1
    print('wrong inference {}/{}'.format(wrong_count, len(test)))


    """Original code referenced from https://github.com/hido/chainer-handson"""
    ROW = 4
    COLUMN = 5
    # show graphical results of first 20 data to understand what's going on in inference stage
    plt.figure(figsize=(15, 10))
    for i in range(ROW * COLUMN):
        # Example of predicting the test input one by one.
        x = Variable(xp.asarray([test[i][0]]))  # test data
        # t = Variable(xp.asarray([test[i][1]]))  # labels
        y = model(x)
        np.set_printoptions(precision=2, suppress=True)
        print('{}-th image: answer = {}, predict = {}'.format(i, test[i][1], F.softmax(y).data))
        prediction = y.data.argmax(axis=1)
        example = (test[i][0] * 255).astype(np.int32).reshape(28, 28)
        plt.subplot(ROW, COLUMN, i+1)
        plt.imshow(example, cmap='gray')
        plt.title("No.{0} / Answer:{1}, Predict:{2}".format(i, test[i][1], prediction))
        plt.axis("off")
    plt.tight_layout()
    plt.savefig('inference.png')


if __name__ == '__main__':
    main()
