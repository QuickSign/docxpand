import argparse
import matplotlib.pyplot as plt
import json


data = json.load(open("/home/qsuser/Work/DocXPand/Expes/unet_v2/results.json", "r"))
plt.boxplot(
    data,
    patch_artist=True,
    labels=["SDL-Net [9]"]
)
plt.ylabel("IoU")
plt.show()
