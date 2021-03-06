# python imports
import os
import re
import logging
import numpy as np
import matplotlib.pyplot as plt
from tensorflow.python.summary.summary_iterator import summary_iterator

# project imports
from .predict import predict

# third-party imports
from ext.lab2im import utils


def validate_training(image_dir,
                      gt_dir,
                      models_dir,
                      validation_main_dir,
                      path_label_list,
                      step_eval=1,
                      recompute=True):
    """This function validates models saved at different epochs of the same training.
    All models are assumed to be in the same folder.contained in models_dir.
    The results of each model are saved in a subfolder in validation_main_dir.
    :param image_dir: path of the folder with validation images.
    :param gt_dir: path of the folder with ground truth label maps.
    These are matched to the validation images by sorting order.
    :param models_dir: path of the folder with the models to validate.
    :param validation_main_dir: path of the folder where all the models validation subfolders will be saved.
    :param path_label_list: path of the numpy array containing all the label values to validate on.
    :param step_eval: (optional) If step_eval > 1 skips models when validating, by validating on models step_eval apart.
    :param recompute: (optional) whether to recompute result files even if they already exists."""

    # create result folder
    if not os.path.exists(os.path.join(validation_main_dir)):
        os.mkdir(validation_main_dir)

    # loop over models
    list_models = utils.list_files(models_dir, expr=['dice', 'h5'], cond_type='and')[::step_eval]
    for model_idx, path_model in enumerate(list_models):

        # build names and create folders
        model_val_dir = os.path.join(validation_main_dir, os.path.basename(path_model).replace('.h5', ''))
        dice_path = os.path.join(model_val_dir, 'dice.npy')
        if not os.path.exists(os.path.join(model_val_dir)):
            os.mkdir(model_val_dir)

        if (not os.path.isfile(dice_path)) | recompute:
            predict(path_images=image_dir,
                    path_model=path_model,
                    path_segmentation_label_list=path_label_list,
                    path_segmentations=model_val_dir,
                    path_posteriors=None,
                    path_volumes=None,
                    gt_folder=gt_dir,
                    cropping=198)


def plot_validation_curves(list_net_validation_dirs, fontsize=18, size_max_circle=100, skip_first_dice_row=True):
    """This function plots the validation curves of several networks, based on the results of validate_training().
    It takes as input a list of validation folders (one for each network), each containing subfolders with dice scores
    for the corresponding validated epoch.
    :param list_net_validation_dirs: list of all the validation folders of the trainings to plot.
    :param fontsize: (optional) fontsize used for the graph.
    :param size_max_circle: (optional) size of the marker for epochs achieveing the best validation scores.
    :param skip_first_dice_row: """

    # loop over architectures
    plt.figure()
    for net_val_dir in list_net_validation_dirs:

        net_name = os.path.basename(os.path.dirname(net_val_dir))
        list_epochs_dir = utils.list_subfolders(net_val_dir, whole_path=False)

        # loop over epochs
        list_net_dice_scores = list()
        list_epochs = list()
        for epoch_dir in list_epochs_dir:

            # build names and create folders
            epoch_dir = os.path.join(net_val_dir, epoch_dir)
            path_epoch_dice = os.path.join(epoch_dir, 'dice.npy')
            if os.path.isfile(path_epoch_dice):
                if skip_first_dice_row:
                    list_net_dice_scores.append(np.mean(np.load(path_epoch_dice)[1:, :]))
                else:
                    list_net_dice_scores.append(np.mean(np.load(path_epoch_dice)))
                list_epochs.append(int(re.sub('[^0-9]', '', epoch_dir)))

        # plot validation scores for current architecture
        if list_net_dice_scores:  # check that archi has been validated for at least 1 epoch
            list_net_dice_scores = np.array(list_net_dice_scores)
            list_epochs = np.array(list_epochs)
            max_score = np.max(list_net_dice_scores)
            epoch_max_score = list_epochs[np.argmax(list_net_dice_scores)]
            print('\n'+net_name)
            print('epoch max score: %d' % epoch_max_score)
            print('max score: %0.2f' % max_score)
            plt.plot(list_epochs, list_net_dice_scores, label=net_name)
            plt.scatter(epoch_max_score, max_score, s=size_max_circle)

    # finalise plot
    plt.tick_params(axis='both', labelsize=fontsize)
    plt.ylabel('Dice scores', fontsize=fontsize)
    plt.xlabel('Epochs', fontsize=fontsize)
    plt.title('Validation curves', fontsize=fontsize)
    plt.legend()
    plt.show()


def draw_learning_curve(path_tensorboard_files, architecture_names, fontsize=18):
    """This function draws the learning curve of several trainings on the same graph.
    :param path_tensorboard_files: list of tensorboard files corresponding to the models to plot.
    :param architecture_names: list of the names of the models
    :param fontsize: (optional) fontsize used for the graph.
    """

    # reformat inputs
    path_tensorboard_files = utils.reformat_to_list(path_tensorboard_files)
    architecture_names = utils.reformat_to_list(architecture_names)
    assert len(path_tensorboard_files) == len(architecture_names), 'names and tensorboard lists should have same length'

    # loop over architectures
    plt.figure()
    for path_tensorboard_file, name in zip(path_tensorboard_files, architecture_names):

        # extract loss at the end of all epochs
        list_losses = list()
        logging.getLogger('tensorflow').disabled = True
        for e in summary_iterator(path_tensorboard_file):
            for v in e.summary.value:
                if v.tag == 'loss' or v.tag == 'accuracy' or v.tag == 'epoch_loss':
                    list_losses.append(v.simple_value)
        plt.plot(1-np.array(list_losses), label=name, linewidth=2)

    # finalise plot
    plt.legend(fontsize=fontsize)
    plt.xlabel('Epochs', fontsize=fontsize)
    plt.ylabel('Soft Dice scores', fontsize=fontsize)
    plt.tick_params(axis='both', labelsize=fontsize)
    plt.title('Learning curves', fontsize=fontsize)
    plt.show()
