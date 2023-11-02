#!/bin/bash

# Arguments
while getopts g: option
do
case "${option}"
in
g) gpu_device=${OPTARG};;
esac
done

# Global Settings
dataset_name=DPA_200MHz
accelerator=cuda
devices=0



# DPD Model
DPD_backbone=dgru
DPD_hidden_size=8
DPD_num_layers=1

# Hyperparameters
seed=0
n_epochs=1
frame_length=50
frame_stride=1
loss_type=l2
opt_type=adamw
batch_size=64
batch_size_eval=256
lr_schedule=1
lr=1e-3
lr_end=1e-6
decay_factor=0.5
patience=10

#########################
# Train PA
#########################
step=train_pa
seed=(0 1 2 3 4)

# PA Model
PA_backbone=(dgru, gru, vdlstm)
PA_hidden_size=8
PA_num_layers=1

for i_seed in "${seed[@]}"; do
    python main.py --dataset_name "$dataset_name" --seed "$i_seed" --step "$step"\
    --accelerator "$accelerator" --devices "$devices"\
    --PA_backbone "$PA_backbone" --PA_hidden_size "$PA_hidden_size" --PA_num_layers "$PA_num_layers"\
    --DPD_backbone "$DPD_backbone" --DPD_hidden_size "$DPD_hidden_size" --DPD_num_layers "$DPD_num_layers"\
    --frame_length "$frame_length" --frame_stride "$frame_stride" --loss_type "$loss_type" --opt_type "$opt_type"\
    --batch_size "$batch_size" --batch_size_eval "$batch_size_eval" --n_epochs "$n_epochs" --lr_schedule "$lr_schedule"\
    --lr "$lr" --lr_end "$lr_end" --decay_factor "$decay_factor" --patience "$patience" || exit 1;
done

# Train DPD
step=train_dpd
seed=(0 1)
for i_seed in "${seed[@]}"; do
    python main.py --dataset_name "$dataset_name" --seed "$i_seed" --step "$step"\
    --accelerator "$accelerator" --devices "$devices"\
    --PA_backbone "$PA_backbone" --PA_hidden_size "$PA_hidden_size" --PA_num_layers "$PA_num_layers"\
    --DPD_backbone "$DPD_backbone" --DPD_hidden_size "$DPD_hidden_size" --DPD_num_layers "$DPD_num_layers"\
    --frame_length "$frame_length" --frame_stride "$frame_stride" --loss_type "$loss_type" --opt_type "$opt_type"\
    --batch_size "$batch_size" --batch_size_eval "$batch_size_eval" --n_epochs "$n_epochs" --lr_schedule "$lr_schedule"\
    --lr "$lr" --lr_end "$lr_end" --decay_factor "$decay_factor" --patience "$patience" || exit 1;
done

# Run DPD
step=run_dpd
seed=(0 1)
for i_seed in "${seed[@]}"; do
    python main.py --dataset_name "$dataset_name" --seed "$i_seed" --step "$step"\
    --accelerator "$accelerator" --devices "$devices"\
    --PA_backbone "$PA_backbone" --PA_hidden_size "$PA_hidden_size" --PA_num_layers "$PA_num_layers"\
    --DPD_backbone "$DPD_backbone" --DPD_hidden_size "$DPD_hidden_size" --DPD_num_layers "$DPD_num_layers"\
    --frame_length "$frame_length" --frame_stride "$frame_stride" --loss_type "$loss_type" --opt_type "$opt_type"\
    --batch_size "$batch_size" --batch_size_eval "$batch_size_eval" --n_epochs "$n_epochs" --lr_schedule "$lr_schedule"\
    --lr "$lr" --lr_end "$lr_end" --decay_factor "$decay_factor" --patience "$patience" || exit 1;
done