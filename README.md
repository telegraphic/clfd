# clfd

``clfd`` stands for Clean Folded Data, and implements smart RFI removal algorithms to be used on folded pulsar search and timing data. These cleaning algorithms were initially developed for a complete re-processing of the High Time Resolution Universe (HTRU) survey. The inner workings of the algorithms are described in the following paper (section 2.4):
["The High Time Resolution Universe survey XIV: Discovery of 23 pulsars through GPU-accelerated reprocessing"](https://arxiv.org/abs/ABCD.1234)

**TODO: Update the link above once the paper is on arXiv.**

### Installation

Clone the repository into the directory of your choice, go to the root directory of clfd, and run

```bash
make install
```

This simply runs ```pip install``` in [editable mode](https://pip.pypa.io/en/latest/reference/pip_install/#editable-installs)

### Python version

The core of ``clfd`` works with both python 2.7 and python 3, but it requires the python bindings of the [PSRCHIVE](http://psrchive.sourceforge.net/) to interact with psrfits archives, and on some systems these work only with python 2.

### Command line usage

There is a ``cleanup.py`` script in the ``apps`` sub-directory that allows batch processing of multiple files / archives at once. For detailed help on command line arguments:

```bash
cd apps/
python cleanup.py -h
```

In the example below, we process all psrchive folded archives in the ``~/folded_data`` directory. The profile
masking algorithm uses the same three features as in the paper with a Tukey parameter (``qmask``) of 2.0.
``--despike`` enables the use of the zero DM spike removal algorithm, which has its own Tukey parameter (``qspike``,
2.0 by default, 4.0 in the example here). The spike removal is turned off by default as there is a small
chance that it could affect pulses from a very bright low-DM pulsar. In the vast majority of cases it is
a good idea to use it though.

```bash
python cleanup.py ~/folded_data/*.ar --format psrchive --features std ptp lfamp --qmask 2.0 --despike --qspike 4.0
```

### Interactive Usage

The ``cleanup.py`` script may be the most practical way of getting the job done, but it just calls functions that are accessible to the user as well. It might be useful to check or plot intermediate outputs. The example below exposes the computation steps: featurization, outlier flagging and application of the outlier mask to the original archive.

```python
>>> import psrchive
>>> import clfd

# Load folded archive produced with PSRCHIVE
>>> archive = psrchive.Archive_load("archive.ar")
>>> cube = clfd.DataCube.from_psrchive(archive)

# Compute chosen profile features.
# The output is a pandas DataFrame with feature names as columns, and (subint, channel) tuples as rows.
>>> features = clfd.featurize(cube, features=('std', 'ptp', 'lfamp'))
>>> print(features)
                     std       ptp     lfamp
subint channel                              
0      0        0.042826  0.224936  0.786012
       1        0.000210  0.003367  0.003367
       2        0.002779  0.006757  0.009283
       3        0.002778  0.006757  0.020955
...                  ...       ...       ...
57     1020     0.050708  0.309764  0.171277
       1021     0.048685  0.272727  0.928349
       1022     0.055210  0.314584  1.463649
       1023     0.058338  0.346801  1.077389

[59392 rows x 3 columns]

# From there, compute profile mask, optionally excluding some known bad channels from the analysis. 
# The example archive here contains Parkes BPSR data, and we know that the first 150 channels are always bad.
>>> stats, mask = clfd.profile_mask(features, q=2.0, zap_channels=range(150))

# 'stats' contains the 1st and 3rd quantiles, inter-quartile range and min/max acceptable values for each feature.
# vmin = q1 - q x iqr
# vmax = q3 + q x iqr
# Where 'q' is the parameter passed to the profile_mask function above.
>>> print(stats)

           std       ptp     lfamp
q1    0.037299  0.202817  0.376125
q3    0.040031  0.235003  0.918363
iqr   0.002733  0.032185  0.542239
vmin  0.031833  0.138447 -0.708352
vmax  0.045497  0.299373  2.002841

# 'mask' is a boolean array of shape (num_subints, num_channels), whose value is True for bad profiles.
# Any frequency channels specified via the 'zap_channels' argument above are forcibly set to True
>>> mask.shape
(58, 1024)

>>> mask
array([[ True,  True,  True, ..., False, False, False],
       [ True,  True,  True, ..., False, False, False],
       [ True,  True,  True, ..., False, False, False],
       ...,
       [ True,  True,  True, ..., False, False, False],
       [ True,  True,  True, ..., False, False, False],
       [ True,  True,  True, ...,  True,  True,  True]])

# Applying the mask to the original archive and saving the output is a format-dependent operation. 
# For each format there is a corresponding Handler class in the clfd.handlers sub-module, which implements methods to apply a mask to the original file and save the output.
>>> from clfd.handlers import PsrchiveHandler

# In PSRCHIVE, every profile has a weight parameter. This sets the weight of every bad profile to 0.
# We can then save the clean data as a new archive in PSRFITS format.
>>> PsrchiveHandler.apply_profile_mask(mask, archive)
>>> PsrchiveHandler.save("archive_clean.ar", archive)

# Optionally, we can then use the zero DM spike removal algorithm. Here the idea is to look for
# outliers in the zero DM time-phase plot, and replace them by appropriate values (inferred 
# from the data) across the frequency dimension.
>>> tpmask, valid_chans, repvals = clfd.time_phase_mask(cube, q=2.0, zap_channels=zap_channels)

# 'mask' is a boolean array of shape (num_subints, num_phase_bins), whose value is True for bad time-phase bins.
# 'valid_chans' is the list of channels NOT included in zap_channels
# 'repvals' is a numpy array with the same shape as the data cube, containing appropriate replacement values
>>> PsrchiveHandler.apply_time_phase_mask(tpmask, valid_chans, repvals, archive)
>>> PsrchiveHandler.save("archive_cleanest.ar", archive)
```
