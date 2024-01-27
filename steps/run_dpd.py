__author__ = "Yizhuo Wu, Chang Gao"
__license__ = "Apache-2.0 License"
__email__ = "yizhuo.wu@tudelft.nl, chang.gao@tudelft.nl"

import os
import pandas as pd
import torch
import models as model
from modules.paths import create_folder
from project import Project
from utils.util import count_net_params
from modules.data_collector import load_dataset


def main(proj: Project):
    ###########################################################################################################
    # Initialization
    ###########################################################################################################
    # Set Accelerator Device
    proj.set_device()

    # Load Dataset
    _, _, _, _, X_test, _ = load_dataset(dataset_name=proj.dataset_name)

    # Create DPD Output Folder
    create_folder(['dpd_out'])

    ###########################################################################################################
    # Network Settings
    ###########################################################################################################
    # Instantiate DPD Model
    net_dpd = model.CoreModel(input_size=2,  # I and Q
                              hidden_size=proj.DPD_hidden_size,
                              num_layers=proj.DPD_num_layers,
                              backbone_type=proj.DPD_backbone)
    n_net_dpd_params = count_net_params(net_dpd)
    print("::: Number of DPD Model Parameters: ", n_net_dpd_params)
    dpd_model_id = proj.gen_dpd_model_id(n_net_dpd_params)

    # Load Pretrained DPD Model
    path_dpd_model = os.path.join('save', proj.dataset_name, 'train_dpd', dpd_model_id + '.pt')
    net_dpd.load_state_dict(torch.load(path_dpd_model))

    # Get parameter count
    n_net_params = count_net_params(net_dpd)
    print("::: Number of Network Parameters: ", n_net_params)

    # Move the network to the proper device
    net_dpd = net_dpd.to(proj.device)

    ###########################################################################################################
    # Run DPD
    ###########################################################################################################
    net_dpd = net_dpd.eval()
    with torch.no_grad():
        # Move test set data to the proper device
        dpd_in = torch.Tensor(X_test).unsqueeze(dim=0).to(proj.device)
        # DPD Model Forward Propagation
        dpd_out = net_dpd(dpd_in)
        # Remove the Batch Dimension
        dpd_out = torch.squeeze(dpd_out)
        # Move dpd_out to CPU
        dpd_out = dpd_out.cpu()

    ###########################################################################################################
    # Export Pre-distorted PA Inputs using the Test Set Data
    ###########################################################################################################
    pa_in = pd.DataFrame({'I': X_test[:, 0], 'Q': X_test[:, 1], 'I_dpd': dpd_out[:, 0], 'Q_dpd': dpd_out[:, 1]})
    path_file_pa_in = os.path.join('dpd_out', dpd_model_id + '.csv')
    pa_in.to_csv(path_file_pa_in, index=False)
    print("DPD outputs saved to the ./dpd_out folder.")
