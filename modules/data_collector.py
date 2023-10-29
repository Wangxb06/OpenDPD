import os
import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset
from sklearn.model_selection import train_test_split


def prepare_segments(args):
    """
    Split the IQ_data into segments of size nperseg. Zero padding is applied
    if the last section is not of length nperseg.
    """
    nperseg = args.nperseg
    path_dataset = os.path.join('data', args.dataset_name)
    # Input = pd.read_csv(os.path.join(data_dict, 'Input80w.csv'))
    # Output = pd.read_csv(os.path.join(data_dict, 'Output80w.csv'))
    train_input = pd.read_csv(os.path.join(path_dataset, 'train_input.csv'))
    train_output = pd.read_csv(os.path.join(path_dataset, 'train_output.csv'))
    val_input = pd.read_csv(os.path.join(path_dataset, 'val_input.csv'))
    val_output = pd.read_csv(os.path.join(path_dataset, 'val_output.csv'))
    test_input = pd.read_csv(os.path.join(path_dataset, 'test_input.csv'))
    test_output = pd.read_csv(os.path.join(path_dataset, 'test_output.csv'))

    def split_segments(IQ_data):
        num_samples = IQ_data.shape[0]
        segments = []
        for i in range(0, num_samples, nperseg):
            segment = IQ_data[i:i + nperseg]
            if segment.shape[0] < nperseg:
                padding_shape = (nperseg - segment.shape[0], 2)
                segment = torch.vstack((segment, torch.zeros(padding_shape)))
            segments.append(segment)
        return np.array(segments)

    train_input_segments = split_segments(train_input)
    train_output_segments = split_segments(train_output)
    val_input_segments = split_segments(val_input)
    val_output_segments = split_segments(val_output)
    test_input_segments = split_segments(test_input)
    test_output_segments = split_segments(test_output)

    return train_input_segments, train_output_segments, val_input_segments, val_output_segments, test_input_segments, test_output_segments


def get_training_frames(segments, seq_len, stride=1):
    """
    For each segment, apply the framing operation.

    Args:
    - segments (3D array): The segments produced by get_ofdm_segments.
    - seq_len (int): The length of each frame.
    - stride (int, optional): The step between frames. Default is 1.

    Returns:
    - 3D array where the first dimension is the total number of frames,
      the second dimension is seq_len, and the third dimension is 2 (I and Q).
    """

    all_frames = []
    for segment in segments:
        num_frames = (segment.shape[0] - seq_len) // stride + 1
        for i in range(num_frames):
            frame = segment[i * stride: i * stride + seq_len]
            all_frames.append(frame)

    return np.array(all_frames)


class IQSegmentDataset(Dataset):
    def __init__(self, PA_IQ_in_segments, PA_IQ_out_segments):
        self.PA_IQ_in_segments = torch.DoubleTensor(PA_IQ_in_segments)
        self.PA_IQ_out_segments = torch.DoubleTensor(PA_IQ_out_segments)

    def __len__(self):
        return len(self.PA_IQ_in_segments)

    def __getitem__(self, idx):
        IQ_in_segment = self.PA_IQ_in_segments[idx, ...]
        IQ_out_segment = self.PA_IQ_out_segments[idx, ...]
        return IQ_in_segment, IQ_out_segment


class IQFrameDataset(Dataset):
    def __init__(self, segment_dataset, frame_length, stride=1):
        """
        Initialize the frame dataset using a subset of IQSegmentDataset.

        Args:
        - segment_dataset (IQSegmentDataset): The pre-split segment dataset.
        - seq_len (int): The length of each frame.
        - stride (int, optional): The step between frames. Default is 1.
        """

        # Extract segments from the segment_dataset
        IQ_in_segments = [item[0] for item in segment_dataset]
        IQ_out_segments = [item[1] for item in segment_dataset]

        # Convert the list of tensors to numpy arrays
        IQ_in_segments = torch.stack(IQ_in_segments).numpy()
        IQ_out_segments = torch.stack(IQ_out_segments).numpy()

        # Convert segments into frames
        self.IQ_in_frames = torch.DoubleTensor(get_training_frames(IQ_in_segments, frame_length, stride))
        self.IQ_out_frames = torch.DoubleTensor(get_training_frames(IQ_out_segments, frame_length, stride))

    def __len__(self):
        return len(self.IQ_in_frames)

    def __getitem__(self, idx):
        return self.IQ_in_frames[idx], self.IQ_out_frames[idx]


def split(In, Out):
    # Get train, validation and test dataset
    X_train, X_tnv, y_train, y_tnv = train_test_split(In, Out, test_size=0.4, random_state=42)
    X_val, X_test, y_val, y_test = train_test_split(X_tnv, y_tnv, test_size=0.5, random_state=42)

    return X_train, y_train, X_val, y_val, X_test, y_test


def data_prepare(X, y, frame_length, degree):
    Input = []
    Output = []
    X = torch.Tensor(X)
    y = torch.Tensor(y)
    for k in range(X.shape[0]):
        Complex_In = torch.complex(X[k, :, 0], X[k, :, 1])
        Complex_Out = torch.complex(y[k, :, 0], y[k, :, 1])
        ulength = len(Complex_In) - frame_length
        Input_matrix = torch.complex(torch.zeros(ulength, frame_length),
                                     torch.zeros(ulength, frame_length))
        degree_matrix = torch.complex(torch.zeros(ulength - frame_length, frame_length * frame_length * degree),
                                      torch.zeros(ulength - frame_length, frame_length * frame_length * degree))
        for i in range(ulength):
            Input_matrix[i, :] = Complex_In[i:i + frame_length]
        for j in range(1, degree):
            for h in range(frame_length):
                degree_matrix[:,
                (j - 1) * frame_length * frame_length + h * frame_length:(j - 1) * frame_length * frame_length + (
                            h + 1) * frame_length] = Input_matrix[:ulength - frame_length] * torch.pow(
                    abs(Input_matrix[h:h + ulength - frame_length, :]), j)
        Input_matrix = torch.cat((Input_matrix[:ulength - frame_length], degree_matrix), dim=1)
        b_output = np.array(Complex_Out[:len(Complex_In) - 2 * frame_length])
        b_input = np.array(Input_matrix)
        Input.append(b_input)
        Output.append(b_output)

    return Input, Output


class IQFrameDataset_gmp(Dataset):
    def __init__(self, segment_dataset, frame_length, degree, stride=1):
        """
        Initialize the frame dataset using a subset of IQSegmentDataset.

        Args:
        - segment_dataset (IQSegmentDataset): The pre-split segment dataset.
        - seq_len (int): The length of each frame.
        - stride (int, optional): The step between frames. Default is 1.
        """

        # Extract segments from the segment_dataset
        IQ_in_segments = [item[0] for item in segment_dataset]
        IQ_out_segments = [item[1] for item in segment_dataset]

        # Convert the list of tensors to numpy arrays
        IQ_in_segments = torch.stack(IQ_in_segments).numpy()
        IQ_out_segments = torch.stack(IQ_out_segments).numpy()

        self.IQ_in_frames, self.IQ_out_frames = data_prepare(IQ_in_segments, IQ_out_segments, frame_length, degree)

    def __len__(self):
        return len(self.IQ_in_frames)

    def __getitem__(self, idx):
        return self.IQ_in_frames[idx], self.IQ_out_frames[idx]
