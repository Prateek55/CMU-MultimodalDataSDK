#!/usr/bin/env python
"""
The file contains the class and methods for loading and aligning datasets
"""
import pickle
import numpy as np
from scipy.io import loadmat
import pandas as pd
import utils
import warnings

__author__ = "Prateek Vij"
__copyright__ = "Copyright 2017, Carnegie Mellon University"
__credits__ = ["Amir Zadeh", "Prateek Vij", "Soujanya Poria"]
__license__ = "GPL"
__version__ = "1.0.1"
__status__ = "Production"


class Dataset():
    """Primary class for loading and aligning dataset"""

    def __init__(self, dataset_file, stored=False, timestamps='absolute'):
        """
        Initialise the Dataset class. Support two loading mechanism - 
        from dataset files and from the pickle file, decided by the param
        stored.
        :param stored: True if loading from pickle, false if loading from 
                       dataset feature files. Default False
        :param dataset_file: Filepath to the file required to load dataset 
                             features. CSV or pickle file depending upon the
                             loading mechanism
        :timestamps: absolute or relative.
        """
        self.feature_dict = None
        self.timestamps = timestamps
        self.stored = stored
        self.dataset_file = dataset_file
        self.phoneme_dict = utils.p2fa_phonemes

    def load(self):
        """
        Loads feature dictionary for the input dataset
        :returns: Dictionary of features for the dataset with each modality 
         as dictionary key
        """

        # Load from the pickle file if stored is True
        if self.stored:
            self.dataset_pickle = self.dataset_file
            self.feature_dict = pickle.load(open(self.dataset_pickle))
            return self.feature_dict

        # Load the feature dictionary from the dataset files
        self.dataset_csv = self.dataset_file
        self.feature_dict = self.controller()
        return self.feature_dict

    def controller(self):
        """
        Validates the dataset csv file and loads the features for the dataset
        from its feature files
        """

        def validate_file(self):
            data = pd.read_csv(self.dataset_csv, header=None)
            data = np.asarray(data)
            #data = data[:,:7]
            self.dataset_info = {}
            modality_count = len(data[0]) - 4
            self.modalities = {}
            for i in range(modality_count):
                key = 'modality_' + str(i)
                info = {}
                info["level"] = str(data[1][i + 4])
                info["type"] = str(data[0][i + 4])
                self.modalities[key] = info

            for record in data[2:]:
                video_id = str(record[0])
                segment_id = str(record[1])
                if video_id not in self.dataset_info:
                    self.dataset_info[video_id] = {}
                if segment_id in self.dataset_info[video_id]:
                    raise NameError("Multiple instances of segment "
                                    + segment_id + " for video " + video_id)
                segment_data = {}
                segment_data["start"] = float(record[2])
                segment_data["end"] = float(record[3])
                for i in range(modality_count):
                    key = 'modality_' + str(i)
                    segment_data[key] = str(record[i + 4])
                self.dataset_info[video_id][segment_id] = segment_data
            return

        def load_features(self):
            feat_dict = {}
            data = self.dataset_info
            modalities = self.modalities
            timestamps = self.timestamps
            for key, value in modalities.iteritems():
                api = value['type']
                level = value['level']
                loader_method = Dataset.__dict__["load_" + api]
                modality_feats = {}
                print "Loading features for ", api
                for video_id, video_data in data.iteritems():
                    video_feats = {}
                    for segment_id, segment_data in video_data.iteritems():
                        filepath = str(segment_data[key])
                        start = segment_data["start"]
                        end = segment_data["end"]
                        video_feats[segment_id] = loader_method(self,
                                                                filepath, start, end, timestamps, level)
                    modality_feats[video_id] = video_feats
                feat_dict[key] = modality_feats

            return feat_dict

        validate_file(self)
        feat_dict = load_features(self)

        return feat_dict

    def load_opensmile(self, filepath, start, end, timestamps='absolute', level='s'):
        """
        Load OpenSmile Features from the file corresponding to the param
        filepath
        :param start: Start time of the segment
        :param end: End time of the segment
        :param filepath: Path to the opensmile feature files
        :param level: 's' if the file contains features only for the segment,
                      i.e. interval (start, end), 'v' if for the entire video 
        :param timestamps: relative or absolute
        :returns: List of tuples (feat_start, feat_end, feat_value)
                  corresponding to the features in the interval.
        Note: Opensmile support features for entire segment or video only and 
              will return None if level is 'v' and start time is 
        """
        features = []
        start_time, end_time = start, end
        if timestamps == 'relative':
            start_time = 0.0
            end_time = end - start

        if level == 's' or start == 0.0:
            feats = open(filepath).readlines()[-1].strip().split(',')[1:]
            feats = [float(feat_val) for feat_val in feats]
            feat_val = np.asarray(feats, dtype=np.float32)
            features.append((start_time, end_time, feat_val))
        else:
            print "Opensmile support features for the entire segment"
            return None
        return features

    def load_covarep(self, filepath, start, end, timestamps='absolute', level='s'):
        """
        Load COVAREP Features from the file corresponding to the param 
        filepath
        :param start: Start time of the segment
        :param end: End time of the segment
        :param filepath: Path to the opensmile feature files
        :param level: 's' if the file contains features only for the segment,
                      i.e. interval (start, end), 'v' if for the entire video 
        :param timestamps: relative or absolute
        :returns: List of tuples (feat_start, feat_end, feat_value)
                  corresponding to the features in the interval.
        """
        features = []
        time_period = 0.01
        f_content = loadmat(filepath)
        feats = f_content['features']
        start_time, end_time = start, end
        if timestamps == "relative":
            start_time, end_time = 0.0, end - start

        if level == 's':
            feat_start = start_time
            for feat in feats:
                feat_end = feat_start + time_period
                feat_val = np.asarray(feat)
                features.append((feat_start, feat_end, feat_val))
                feat_start += time_period
        else:
            feat_count = feats.shape[0]
            start_index = int(min((start / time_period), feat_count))
            end_index = int(min((end / time_period), feat_count))
            feat_start = start_time
            for feat in feats[start_index:end_index]:
                feat_end = feat_start + time_period
                feat_val = np.asarray(feat)
                features.append((feat_start, feat_end, feat_val))
                feat_start += time_period
        return features

    def load_phonemes(self, filepath, start, end, timestamps='absolute', level='v'):
        """
        Load P2FA phonemes as Features from the file corresponding to the 
        param filepath
        :param start: Start time of the segment
        :param end: End time of the segment
        :param filepath: Path to the opensmile feature files
        :param level: 's' if the file contains features only for the segment,
                      i.e. interval (start, end), 'v' if for the entire video 
        :param timestamps: relative or absolute
        :returns: List of tuples (feat_start, feat_end, feat_value)
                  corresponding to the features in the interval.
        """
        features = []
        start_time, end_time = start, end
        if timestamps == "relative":
            start_time, end_time = 0.0, end - start

        if level == 's':
            with open(filepath, 'r') as f_handle:
                for line in f_handle.readlines():
                    line = line.strip()
                    if not line:
                        break
                    feat_start = float(line.split(",")[1]) + start_time
                    feat_end = float(line.split(",")[2]) + start_time
                    feat_val = [float(val) for val in line.split(",")[3:]]
                    feat_val = np.asarray(feat_val)
                    features.append((feat_start, feat_end, feat_val))
        else:
            with open(filepath, 'r') as f_handle:
                for line in f_handle.readlines():
                    line = line.strip()
                    if not line:
                        break
                    feat_start = float(line.split(",")[1])
                    feat_end = float(line.split(",")[2])
                    feat_time = feat_end - feat_start
                    if ((feat_start <= start and feat_end > end)
                        or (feat_start >= start and feat_end < end)
                        or (feat_start <= start
                            and start - feat_start < feat_time / 2)
                        or (feat_start >= start
                            and end - feat_start > feat_time / 2)):

                        feat_start = feat_start - start + start_time
                        feat_end = feat_end - start + start_time
                        feat_val = [float(val) for val in line.split(",")[3:]]
                        feat_val = np.asarray(feat_val)
                        features.append((feat_start, feat_end, feat_val))
        return features

    def load_embeddings(self, filepath, start, end, timestamps='absolute', level='v'):
        """
        Load Word Embeddings from the file corresponding to the param 
        filepath
        :param start: Start time of the segment
        :param end: End time of the segment
        :param filepath: Path to the opensmile feature files
        :param level: 's' if the file contains features only for the segment,
                      i.e. interval (start, end), 'v' if for the entire video 
        :param timestamps: relative or absolute
        :returns: List of tuples (feat_start, feat_end, feat_value)
                  corresponding to the features in the interval.
        """
        features = []
        start_time, end_time = start, end
        if timestamps == "relative":
            start_time, end_time = 0.0, end - start

        if level == 's':
            with open(filepath, 'r') as f_handle:
                for line in f_handle.readlines():
                    line = line.strip()
                    if not line:
                        break
                    feat_start = float(line.split(",")[0]) + start_time
                    feat_end = float(line.split(",")[1]) + start_time
                    feat_val = [float(val) for val in line.split(",")[2:]]
                    feat_val = np.asarray(feat_val)
                    features.append((feat_start, feat_end, feat_val))
        else:
            with open(filepath, 'r') as f_handle:
                for line in f_handle.readlines():
                    line = line.strip()
                    if not line:
                        break
                    feat_start = float(line.split(",")[1])
                    feat_end = float(line.split(",")[2])
                    feat_time = feat_end - feat_start
                    if ((feat_start <= start and feat_end > end)
                        or (feat_start >= start and feat_end < end)
                        or (feat_start <= start
                            and start - feat_start < feat_time / 2)
                        or (feat_start >= start
                            and end - feat_start > feat_time / 2)):

                        feat_start = feat_start - start + start_time
                        feat_end = feat_end - start + start_time
                        feat_val = [float(val) for val in line.split(",")[3:]]
                        feat_val = np.asarray(feat_val)
                        features.append((feat_start, feat_end, feat_val))
        return features

    def load_words(self, filepath, start, end, timestamps='absolute', level='v'):
        """
        Load one hot embeddings for words as features from the file 
        corresponding to the param filepath
        :param start: Start time of the segment
        :param end: End time of the segment
        :param filepath: Path to the opensmile feature files
        :param level: 's' if the file contains features only for the segment,
                      i.e. interval (start, end), 'v' if for the entire video 
        :param timestamps: relative or absolute
        :returns: List of tuples (feat_start, feat_end, feat_value)
                  corresponding to the features in the interval.
        """
        features = []
        start_time, end_time = start, end
        if timestamps == "relative":
            start_time, end_time = 0.0, end - start

        if level == 's':
            with open(filepath, 'r') as f_handle:
                for line in f_handle.readlines():
                    line = line.strip()
                    if not line:
                        break
                    feat_start = float(line.split(",")[0]) + start_time
                    feat_end = float(line.split(",")[1]) + start_time
                    feat_val = [float(val) for val in line.split(",")[2:]]
                    feat_val = np.asarray(feat_val)
                    #print (feat_start, feat_end)
                    #assert False
                    features.append((feat_start, feat_end, feat_val))
        else:
            with open(filepath, 'r') as f_handle:
                for line in f_handle.readlines():
                    line = line.strip()
                    if not line:
                        break
                    feat_start = float(line.split(",")[1])
                    feat_end = float(line.split(",")[2])
                    feat_time = feat_end - feat_start
                    if ((feat_start <= start and feat_end > end)
                        or (feat_start >= start and feat_end < end)
                        or (feat_start <= start
                            and start - feat_start < feat_time / 2)
                        or (feat_start >= start
                            and end - feat_start > feat_time / 2)):

                        feat_start = feat_start - start + start_time
                        feat_end = feat_end - start + start_time
                        feat_val = [float(val) for val in line.split(",")[3:]]
                        feat_val = np.asarray(feat_val)
                        features.append((feat_start, feat_end, feat_val))
        return features

    def load_openface(self, filepath, start, end, timestamps='absolute', level='v'):
        """
        Load OpenFace features from the file corresponding to the param 
        filepath
        :param start: Start time of the segment
        :param end: End time of the segment
        :param filepath: Path to the opensmile feature files
        :param level: 's' if the file contains features only for the segment,
                      i.e. interval (start, end), 'v' if for the entire video 
        :param timestamps: relative or absolute
        :returns: List of tuples (feat_start, feat_end, feat_value)
                  corresponding to the features in the interval.
        """
        features = []
        time_period = 0.0333333

        start_time, end_time = start, end
        if timestamps == "relative":
            start_time, end_time = 0.0, end - start

        if level == 's':
            with open(filepath, 'r') as f_handle:
                for line in f_handle.readlines()[1:]:
                    line = line.strip()
                    if not line:
                        break
                    feat_start = float(line.split(",")[0]) + start_time
                    feat_end = feat_start + time_period
                    feat_val = [float(val) for val in line.split(",")[1:]]
                    feat_val = np.asarray(feat_val, dtype=np.float32)
                    features.append((feat_start, feat_end, feat_val))

        else:
            with open(filepath, 'r') as f_handle:
                for line in f_handle.readlines()[1:]:
                    line = line.strip()
                    if not line:
                        break
                    feat_start = float(line.split(",")[1])

                    if (feat_start >= start and feat_start < end):
                        # To adjust the timestamps
                        feat_start = feat_start - start + start_time
                        feat_end = feat_start + time_period
                        feat_val = [float(val) for val in line.split(",")[2:]]
                        feat_val = np.asarray(feat_val, dtype=np.float32)
                        features.append((feat_start, feat_end, feat_val))
        return features

    def load_old_facet(self, filepath, start, end, timestamps='absolute', level='v'):
        """
        Load FACET features from the file corresponding to the param 
        filepath
        :param start: Start time of the segment
        :param end: End time of the segment
        :param filepath: Path to the opensmile feature files
        :param level: 's' if the file contains features only for the segment,
                      i.e. interval (start, end), 'v' if for the entire video 
        :param timestamps: relative or absolute
        :returns: List of tuples (feat_start, feat_end, feat_value)
                  corresponding to the features in the interval.
        """
        features = []
        time_period = 0.03333

        start_time, end_time = start, end
        if timestamps == "relative":
            start_time, end_time = 0.0, end - start

        if level == 's':
            with open(filepath, 'r') as f_handle:
                for line in f_handle.readlines()[1:]:
                    line = line.strip()
                    if not line:
                        break
                    feat_start = float(line.split(",")[0]) + start_time
                    feat_end = feat_start + time_period
                    feat_val = [float(val) for val in line.split(",")[1:]]
                    feat_val = np.asarray(feat_val, dtype=np.float32)
                    features.append((feat_start, feat_end, feat_val))

        else:
            with open(filepath, 'r') as f_handle:
                for line in f_handle.readlines()[1:]:
                    line = line.strip()
                    if not line:
                        break
                    feat_start = float(line.split(",")[0])

                    if (feat_start >= start and feat_start < end):
                        # To adjust the timestamps
                        feat_start = feat_start - start + start_time
                        feat_end = feat_start + time_period
                        feat_val = [float(val) for val in line.split(",")[1:]]
                        feat_val = np.asarray(feat_val, dtype=np.float32)
                        features.append((feat_start, feat_end, feat_val))
        return features

    # note that this is implicity new facet
    def load_facet(self, filepath, start, end, timestamps='absolute', level='v'):
        """
        Load FACET features from the file corresponding to the param 
        filepath
        :param start: Start time of the segment
        :param end: End time of the segment
        :param filepath: Path to the opensmile feature files
        :param level: 's' if the file contains features only for the segment,
                      i.e. interval (start, end), 'v' if for the entire video 
        :param timestamps: relative or absolute
        :returns: List of tuples (feat_start, feat_end, feat_value)
                  corresponding to the features in the interval.
        """
        features = []
        time_period = 0.03333

        start_time, end_time = start, end
        if timestamps == "relative":
            start_time, end_time = 0.0, end - start

        if level == 's':
            with open(filepath, 'r') as f_handle:
                for line in f_handle.readlines()[1:]:
                    line = line.strip()
                    if not line:
                        break
                    feat_start = float(line.split(",")[1]) + start_time
                    feat_end = feat_start + time_period
                    feat_val = [float(val) for val in line.split(",")[2:-1]]
                    feat_val = np.asarray(feat_val, dtype=np.float32)
                    features.append((feat_start, feat_end, feat_val))

        else:
            with open(filepath, 'r') as f_handle:
                for line in f_handle.readlines()[1:]:
                    line = line.strip()
                    if not line:
                        break
                    feat_start = float(line.split(",")[0])

                    if (feat_start >= start and feat_start < end):
                        # To adjust the timestamps
                        feat_start = feat_start - start + start_time
                        feat_end = feat_start + time_period
                        # print line.split(",")[1:-1]
                        #assert False
                        feat_val = []
                        for val in line.split(",")[1:-1]:
                            try:
                                feat_val.append(float(val))
                            except:
                                feat_val.append(0.0)
                        #feat_val = [float(val) for val in line.split(",")[2:-1]]
                        feat_val = np.asarray(feat_val, dtype=np.float32)
                        features.append((feat_start, feat_end, feat_val))
        return features

    def load_facet1(self, filepath, start, end, timestamps='absolute', level='v'):
        """
        Load FACET features from the file corresponding to the param 
        filepath
        :param start: Start time of the segment
        :param end: End time of the segment
        :param filepath: Path to the opensmile feature files
        :param level: 's' if the file contains features only for the segment,
                      i.e. interval (start, end), 'v' if for the entire video 
        :param timestamps: relative or absolute
        :returns: List of tuples (feat_start, feat_end, feat_value)
                  corresponding to the features in the interval.
        """
        features = []
        time_period = 0.03333

        start_time, end_time = start, end
        if timestamps == "relative":
            start_time, end_time = 0.0, end - start

        if level == 's':
            with open(filepath, 'r') as f_handle:
                for line in f_handle.readlines()[0:]:
                    line = line.strip()
                    if not line:
                        break
                    feat_start = float(line.split(",")[1]) + start_time
                    feat_end = feat_start + time_period
                    feat_val = [float(val) for val in line.split(",")[2:-1]]
                    feat_val = np.asarray(feat_val, dtype=np.float32)
                    features.append((feat_start, feat_end, feat_val))

        else:
            with open(filepath, 'r') as f_handle:
                for line in f_handle.readlines()[0:]:
                    line = line.strip()
                    if not line:
                        break
                    feat_start = float(line.split(",")[1])

                    if (feat_start >= start and feat_start < end):
                        # To adjust the timestamps
                        feat_start = feat_start - start + start_time
                        feat_end = feat_start + time_period
                        # print line.split(",")[1:-1]
                        #assert False
                        feat_val = []
                        for val in line.split(",")[2:-1]:
                            try:
                                feat_val.append(float(val))
                            except:
                                feat_val.append(0.0)
                        #feat_val = [float(val) for val in line.split(",")[2:-1]]
                        feat_val = np.asarray(feat_val, dtype=np.float32)
                        features.append((feat_start, feat_end, feat_val))
        return features

    def load_facet2(self, filepath, start, end, timestamps='absolute', level='v'):
        """
        Load FACET features from the file corresponding to the param 
        filepath
        :param start: Start time of the segment
        :param end: End time of the segment
        :param filepath: Path to the opensmile feature files
        :param level: 's' if the file contains features only for the segment,
                      i.e. interval (start, end), 'v' if for the entire video 
        :param timestamps: relative or absolute
        :returns: List of tuples (feat_start, feat_end, feat_value)
                  corresponding to the features in the interval.
        """
        features = []
        time_period = 0.03333

        start_time, end_time = start, end
        if timestamps == "relative":
            start_time, end_time = 0.0, end - start

        if level == 's':
            with open(filepath, 'r') as f_handle:
                for line in f_handle.readlines()[0:]:
                    line = line.strip()
                    if not line:
                        break
                    feat_start = float(line.split(",")[1]) + start_time
                    feat_end = feat_start + time_period
                    feat_val = [float(val) for val in line.split(",")[2:-1]]
                    feat_val = np.asarray(feat_val, dtype=np.float32)
                    features.append((feat_start, feat_end, feat_val))

        else:
            with open(filepath, 'r') as f_handle:
                for line in f_handle.readlines()[0:]:
                    line = line.strip()
                    if not line:
                        break
                    feat_start = float(line.split(",")[1])

                    if (feat_start >= start and feat_start < end):
                        # To adjust the timestamps
                        feat_start = feat_start - start + start_time
                        feat_end = feat_start + time_period
                        # print line.split(",")[1:-1]
                        #assert False
                        feat_val = []
                        for val in line.split(",")[2:-1]:
                            try:
                                feat_val.append(float(val))
                            except:
                                feat_val.append(0.0)
                        #feat_val = [float(val) for val in line.split(",")[2:-1]]
                        feat_val = np.asarray(feat_val, dtype=np.float32)
                        features.append((feat_start, feat_end, feat_val))
        return features


    def load_misc(self, filepath, start, end, timestamps='absolute', level='v'):
        """
        Load customizable time-distributed features from the file
        corresponding to the param filepath
        :param start: Start time of the segment
        :param end: End time of the segment
        :param filepath: Path to the time-distributed misc feature files
        :param level: 's' if the file contains features only for the segment,
                      i.e. interval (start, end), 'v' if for the entire video
        :param timestamps: relative or absolute
        :returns: List of tuples (feat_start, feat_end, feat_value)
                  corresponding to the features in the interval.
        """
        features = []
        start_time, end_time = start, end
        if timestamps == "relative":
            start_time, end_time = 0.0, end - start

        if level == 's':
            with open(filepath, 'r') as f_handle:
                for line in f_handle.readlines():
                    line = line.strip()
                    if not line:
                        break
                    feat_start = float(line.split(",")[0]) + start_time
                    feat_end = float(line.split(",")[1]) + start_time
                    feat_val = [float(val) for val in line.split(",")[2:]]
                    feat_val = np.asarray(feat_val)
                    #print (feat_start, feat_end)
                    #assert False
                    features.append((feat_start, feat_end, feat_val))
        else:
            with open(filepath, 'r') as f_handle:
                for line in f_handle.readlines():
                    line = line.strip()
                    if not line:
                        break
                    feat_start = float(line.split(",")[0])
                    feat_end = float(line.split(",")[1])
                    feat_time = feat_end - feat_start
                    if ((feat_start <= start and feat_end > end)
                        or (feat_start >= start and feat_end < end)
                        or (feat_start <= start
                            and start - feat_start < feat_time / 2)
                        or (feat_start >= start
                            and end - feat_start > feat_time / 2)):

                        feat_start = feat_start - start + start_time
                        feat_end = feat_end - start + start_time
                        feat_val = [float(val) for val in line.split(",")[3:]]
                        feat_val = np.asarray(feat_val)
                        features.append((feat_start, feat_end, feat_val))
        return features


    def align(self, align_modality):
        aligned_feat_dict = {}
        modalities = self.modalities
        alignments = self.get_alignments(align_modality)
        for modality in modalities:
            if modality == align_modality:
                continue
            aligned_modality = self.align_modality(modality, alignments)
            aligned_feat_dict[modality] = aligned_modality
        self.aligned_feature_dict = aligned_feat_dict
        return aligned_feat_dict

    def get_alignments(self, modality):
        alignments = {}
        aligned_feat_dict = self.feature_dict[modality]

        for video_id, segments in aligned_feat_dict.iteritems():
            segment_alignments = {}
            for segment_id, features in segments.iteritems():
                segment_alignments[segment_id] = []
                for value in features:
                    timing = (value[0], value[1])
                    segment_alignments[segment_id].append(timing)
            alignments[video_id] = segment_alignments
        return alignments

    def align_modality(self, modality, alignments, merge_type="mean"):
        aligned_feat_dict = {}
        modality_feat_dict = self.feature_dict[modality]
        warning_hist = set() # Keep track of all the warnings

        for video_id, segments in alignments.iteritems():
            aligned_video_feats = {}

            for segment_id, feat_intervals in segments.iteritems():
                aligned_segment_feat = []

                for start_interval, end_interval in feat_intervals:
                    time_interval = end_interval - start_interval
                    feats = modality_feat_dict[video_id][segment_id]
                    try:
                        a = len(feats[0][2])
                    except:
                        if (video_id, segment_id) not in warning_hist:
                            print "\nModality {} for video {} segment {} is (partially) missing and is thus being replaced by zeros!\n".format(modality.split("_")[-1], video_id, segment_id)
                            warning_hist.add((video_id, segment_id))
                        # print modality, video_id, segment_id, feats
                        feats = modality_feat_dict[video_id][str(
                            int(segment_id) - 1)]
                    #assert False
                    aligned_feat = np.zeros(len(feats[0][2]))

                    for feat_tuple in feats:
                        feat_start = feat_tuple[0]
                        feat_end = feat_tuple[1]
                        feat_val = feat_tuple[2]
                        if (feat_start < end_interval
                                and feat_end >= start_interval):
                            feat_weight = (min(end_interval, feat_end) -
                                           max(start_interval, feat_start)) / time_interval
                            weighted_feat = np.multiply(feat_val, feat_weight)
                            aligned_feat = np.add(aligned_feat, weighted_feat)

                    aligned_feat_tuple = (start_interval, end_interval,
                                          aligned_feat)
                    aligned_segment_feat.append(aligned_feat_tuple)
                aligned_video_feats[segment_id] = aligned_segment_feat
            aligned_feat_dict[video_id] = aligned_video_feats

        return aligned_feat_dict
