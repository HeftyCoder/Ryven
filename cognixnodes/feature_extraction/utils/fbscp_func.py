from __future__ import annotations
from collections.abc import Mapping, Sequence
import numpy as np
import scipy
import scipy.linalg as la
from sklearn.feature_selection import mutual_info_classif as MIBIF

class FBCSP_binary():
    
    def __init__(self,data_dict:dict,fs:float,n_w:int=2,n_features:int=4,freqs_bands:Sequence=None,n_splits_freq:int=None,filter_order:int=3):
        self.fs = fs
        self.trials_dict = data_dict
        self.n_w = n_w
        self.n_features = n_features
        self.n_trials_class_1 = data_dict[list(data_dict.keys())[0]].shape[0]
        self.n_trials_class_2 = data_dict[list(data_dict.keys())[1]].shape[0]
        
        print(self.n_trials_class_1)
        print()
        print(self.n_trials_class_2)
        
        self.filter_order = filter_order
        
        self.filtered_band_signal_list = []
        
        if isinstance(freqs_bands,np.ndarray):
            if n_splits_freq:
                self.freqs = np.linspace(freqs_bands[0],freqs_bands[1],n_splits_freq)
            else:
                self.freqs = freqs_bands
            
        elif not freqs_bands:
            self.freqs = np.linspace(4,40,10)
        
        else:
            raise ValueError('freqs_band must be an array')
        
        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        
    def extract_features(self):
        #Filter data section
        
        self.FilterBandFunction(self.filter_order)
        
                # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -    
        # CSP filters evaluation and application
        
        # CSP filter evaluation
        self.W_list_band = []
        self.EvaluateW()
        
        # CSP filter application
        self.features_band_list = []
        self.SpatialFilteringAndFeatureExtraction()
        print(self.classifier_features)
        return self.classifier_features
        
        
    def FilterBandFunction(self,filter_order:int=3):
        """
        Function that apply fhe fitlering for each pair of frequencies in the list self.freqs.
        The results are saved in a list called self.filtered_band_signal_list. Each element of the list is a diciotinary with key the label of the various class.

        Parameters
        ----------
        filter_order : int, optional
            The order of the filter. The default is 3.

        """
        # Cycle through the frequency bands
        for i in range(len(self.freqs)-1):
            # Dict for selected band that will contain the various filtered signals
            filt_trial_dict = {}
            
            # "Create" the band
            band = [self.freqs[i], self.freqs[i+1]]
            
            # Cycle for the classes
            for key in self.trials_dict.keys(): 
                # Filter the signal in each class for the selected frequency band
                filt_trial_dict[key] = self.BandFilterTrials(self.trials_dict[key], band[0], band[1], filter_order = filter_order)
            
            # Save the filtered signal in the list
            self.filtered_band_signal_list.append(filt_trial_dict)
            
    def BandFilterTrials(self,trials_matrix:np.ndarray,low_f:float,high_f:float,filter_order:int=3):
        """
        Applying a pass-band fitlering to the data. The filter implementation was done with scipy.signal
    
        Parameters
        ----------
        trials_matrix : numpy matrix
            Numpy matrix with the various EEG trials. The dimensions of the matrix must be n_trial x n_channel x n_samples
        fs : int/double
            Frequency sampling.
        low_f : int/double
            Low band of the pass band filter.
        high_f : int/double
            High band of the pass band filter..
        filter_order : int, optional
            Order of the filter. The default is 3.
    
        Returns
        -------
        filter_trails_matrix : numpy matrix
             Numpy matrix with the various filtered EEG trials. The dimensions of the matrix must be n_trial x n_channel x n_samples.
    
        """
        
        # Evaluate low buond and high bound in the [0, 1] range
        low_bound = low_f / (self.fs/2)
        high_bound = high_f / (self.fs/2)
        
        # Check input data
        if(low_bound < 0): low_bound = 0
        if(high_bound > 1): high_bound = 1
        if(low_bound > high_bound): low_bound, high_bound = high_bound, low_bound
        if(low_bound == high_bound): low_bound, high_bound = 0, 1
        
        b, a = scipy.signal.butter(filter_order, [low_bound, high_bound], 'bandpass')
          
        return scipy.signal.filtfilt(b, a, trials_matrix)
    

    def EvaluateW(self):
        """
        Evaluate the spatial filter of the CSP algorithm for each filtered signal inside self.filtered_band_signal_list
        Results are saved inside self.W_list_band.    
        """
        
        for filt_trial_dict in self.filtered_band_signal_list:
            # Retrieve the key (class)
            
            
            keys = list(filt_trial_dict.keys())
            trials_1 = filt_trial_dict[keys[0]]
            trials_2 = filt_trial_dict[keys[1]]
        
            # Evaluate covariance matrix for the two classes
            cov_1 = self.TrialCovariance(trials_1)
            cov_2 = self.TrialCovariance(trials_2)
            R = cov_1 + cov_2
            
            # Evaluate whitening matrix
            P = self.Whitening(R)
            
            # The mean covariance matrices may now be transformed
            cov_1_white = np.dot(P, np.dot(cov_1, np.transpose(P)))
            cov_2_white = np.dot(P, np.dot(cov_2, np.transpose(P)))
            
            # Since CSP requires the eigenvalues and eigenvector be sorted in descending order we find and sort the generalized eigenvalues and eigenvector
            E, U = la.eig(cov_1_white, cov_2_white)
            order = np.argsort(E)
            order = order[::-1]
            E = E[order]
            U = U[:, order]
            
            # The projection matrix (the spatial filter) may now be obtained
            W = np.dot(np.transpose(U), P)
            
            self.W_list_band.append(W)
            
    def TrialCovariance(self,trials:np.ndarray):
        """
        Calculate the covariance for each trial and return their average
    
        Parameters
        ----------
        trials : numpy 3D-matrix
            Trial matrix. The dimensions must be trials x channel x samples
    
        Returns
        -------
        mean_cov : Numpy matrix
            Mean of the covariance alongside channels.
    
        """
        n_trials, n_channels, n_samples = trials.shape
        
        covariance_matrix = np.zeros((n_trials, n_channels, n_channels))
        
        for i in range(trials.shape[0]):
            trial = trials[i, :, :]
            covariance_matrix[i, :, :] = np.cov(trial)
            
        mean_cov = np.mean(covariance_matrix, 0)
            
        return mean_cov
    
    def Whitening(self,sigma:np.ndarray,mode:int=2):
        """
        Calculate the whitening matrix for the input matrix sigma
    
        Parameters
        ----------
        sigma : Numpy square matrix
            Input matrix.
        mode : int, optional
            Select how to evaluate the whitening matrix. The default is 1.
    
        Returns
        -------
        x : Numpy square matrix
            Whitening matrix.
        """
        [u, s, vh] = np.linalg.svd(sigma)
        
          
        if(mode != 1 and mode != 2): mode == 1
        
        if(mode == 1):
            # Whitening constant: prevents division by zero
            epsilon = 1e-5
            
            # ZCA Whitening matrix: U * Lambda * U'
            x = np.dot(u, np.dot(np.diag(1.0/np.sqrt(s + epsilon)), u.T))
        else:
            # eigenvalue decomposition of the covariance matrix
            d, V = np.linalg.eigh(sigma)
            fudge = 10E-18
         
            # A fudge factor can be used so that eigenvectors associated with small eigenvalues do not get overamplified.
            D = np.diag(1. / np.sqrt(d+fudge))
         
            # whitening matrix
            x = np.dot(np.dot(V, D), V.T)
            
        return x
        
    def SpatialFilteringAndFeatureExtraction(self):
        # Cycle through frequency band and relative CSP filter
        for filt_trial_dict, W in zip(self.filtered_band_signal_list, self.W_list_band):
            # Features dict for the current frequency band
            features_dict = {}
            
            # Cycle through the classes
            for key in filt_trial_dict.keys():
                # Applying spatial filter
                tmp_trial = self.SpatialFilteringW(filt_trial_dict[key], W)
                
                # Features evaluation
                features_dict[key] = self.LogVarEvaluation(tmp_trial)
            
            self.features_band_list.append(features_dict)
        
        # Evaluate mutual information between features
        self.mutual_information_list = self.ComputeFeaturesMutualInformation()
        self.mutual_information_vector, self.other_info_matrix = self.ChangeShapeMutualInformationList()
        
        # Select features to use for classification
        # List of tuple (each tuple contains the number of the band and the number of the features)
        self.classifier_features = self.SelectFeatures()
        
    def SpatialFilteringW(self, trials, W):
        # Allocate memory for the spatial fitlered trials
        trials_csp = np.zeros(trials.shape)
        
        # Apply spatial fitler
        for i in range(trials.shape[0]): trials_csp[i, :, :] = W.dot(trials[i, :, :])
            
        return trials_csp 
        
    def LogVarEvaluation(self, trials):
        """
        Evaluate the log (logarithm) var (variance) of the trial matrix along the samples axis.
        The sample axis is the axis number 2, counting axis as 0,1,2. 
    
        Parameters
        ----------
        trials : numpy 3D-matrix
            Trial matrix. The dimensions must be trials x channel x samples
    
        Returns
        -------
        features : Numpy 2D-matrix
            Return the features matrix. DImension will be trials x (n_w * 2)
    
        """
        # Select the first and last n rows of the CSP filtered signal
        idx = []
        for i in range(self.n_w): idx.append(i)
        for i in reversed(idx): idx.append(-(i + 1))
        trials = trials[:, idx, :]    
        
        features = np.var(trials, 2)
        features = np.log(features)
        
        return features
    
    
    def ComputeFeaturesMutualInformation(self):
        """
        Select the first and last n columns of the various features matrix and compute their mutual inforamation.
        The value of n is self.n_features

        Returns
        -------
        mutual_information_list : List of numpy matrix
            List with the mutual information of the various features.

        """
        
        mutual_information_list = []
                
        # Cycle through the different band
        for features_dict in self.features_band_list:
            # Retrieve features for that band
            keys = list(features_dict.keys())
            feat_1 = features_dict[keys[0]]
            feat_2 = features_dict[keys[1]]
            
            # Save features in a single matrix
            all_features = np.zeros((feat_1.shape[0] + feat_2.shape[0], feat_1.shape[1]))            
            all_features[0:feat_1.shape[0], :] = feat_1
            all_features[feat_1.shape[0]:, :] = feat_2
            
            # Create label vector
            label = np.ones(all_features.shape[0])
            label[0:feat_1.shape[0]] = 2
            
            tmp_mutual_information = MIBIF(all_features, label)
            mutual_information_list.append(tmp_mutual_information)
            
        return mutual_information_list
    
    
    def ChangeShapeMutualInformationList(self):
        # 1D-Array with all the mutual information value
        mutual_information_vector = np.zeros(9 * 2 * self.n_w)
            
        # Since the CSP features are coupled (First with last etc) in this matrix I save the couple.
        # I will also save the original band and the position in the original band
        other_info_matrix = np.zeros((len(mutual_information_vector), 4))
        
        for i in range(len(self.mutual_information_list)):
            mutual_information = self.mutual_information_list[i]
            
            for j in range(self.n_w * 2):
                # Acual index for the various vector
                actual_idx = i * self.n_w * 2 + j
                
                # Save the current value of mutual information for that features
                mutual_information_vector[actual_idx] = mutual_information[j]
                
                # Save other information related to that feature
                other_info_matrix[actual_idx, 0] = i * self.n_w * 2 + ((self.n_w * 2) - (j + 1)) # Position of the twin (in the vector)
                other_info_matrix[actual_idx, 1] = actual_idx # Position of the actual feature (in the vector)
                other_info_matrix[actual_idx, 2] = i # Current band
                other_info_matrix[actual_idx, 3] = j # Position in the original band
                
        return mutual_information_vector, other_info_matrix
        
    
    def SelectFeatures(self):
        """
        Select n features for classification. In this case n is equal to 2 * self.n_features.
        The features selected are the self.n_features with the highest mutual information. 
        Since the CSP features are coupled if the original couple was not selected we add to the list of features the various couple.
        The original algorithm select a variable number of features (and also the V3 implementation has the same behavior). This version select always 2 * self.n_features.
        
        Returns
        -------
        complete_list_of_features : List of tuple
            List that contatin the band for the filter and the position inside the original band.

        """
        
        # Sort features in order of mutual information
        sorted_MI_features_index = np.flip(np.argsort(self.mutual_information_vector))
        sorted_other_info = self.other_info_matrix[sorted_MI_features_index, :]
        
        complete_list_of_features = []
        selected_features = sorted_other_info[:, 1][0:self.n_features]
        
        for i in range(self.n_features):
            # Current features (NOT USED)(added just for clarity during coding)
            # current_features = sorted_other_info[i, 1]
            
            # Twin/Couple feature of the current features
            current_features_twin = sorted_other_info[i, 0]
            
            if(current_features_twin in selected_features): 
                # If I also select its counterpart I only add the current feaures because the counterpart will be added in future iteration of the cycle
                
                # Save the features as tuple with (original band, original position in the original band)
                features_item = (int(sorted_other_info[i, 2]), int(sorted_other_info[i, 3]))
                
                # Add the element to the features vector
                complete_list_of_features.append(features_item)
            else: 
                # If I not select its counterpart I addo both the current features and it's counterpart
                
                # Select and add the current feature
                features_item = (int(sorted_other_info[i, 2]), int(sorted_other_info[i, 3]))
                complete_list_of_features.append(features_item)
                
                # Select and add the twin/couple feature
                idx = sorted_other_info[:, 1] == current_features_twin
                features_item = (int(sorted_other_info[idx, 2][0]), int(sorted_other_info[idx, 3][0]))
                complete_list_of_features.append(features_item)
                
        return sorted(complete_list_of_features)


