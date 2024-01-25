import argparse
import os
import time

import cv2
import lpips
import numpy as np
import pandas


def resize_image_keep_ratio_and_pad(
    img,
    dim: int,
):
    """Resizes an image keeping the aspect ratio unchanged.

    dim: resize the image such that it's dim*dim

    Returns:
            image: the resized image
    """
    height, width = img.shape[:2]
    scale = 1.0
    padding = [(0, 0), (0, 0), (0, 0)]
    scale = dim / max(height, width)
    new_image = cv2.resize(
        img,
        (round(height * scale), round(width * scale)),
        interpolation=cv2.INTER_AREA,
    )
    height, width = new_image.shape[:2]
    top_pad = (dim - height) // 2
    bottom_pad = dim - height - top_pad
    left_pad = (dim - width) // 2
    right_pad = dim - width - left_pad
    padding = [
        (int(top_pad), int(bottom_pad)),
        (int(left_pad), int(right_pad)),
        (0, 0),
    ]
    new_image = np.pad(
        new_image, padding, mode="constant", constant_values=0
    )  # type: ignore
    return new_image


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("-d0", "--dir0", type=str, required=True)
    parser.add_argument("-d1", "--dir1", type=str, required=True)
    parser.add_argument("-o", "--out", type=str, default="./output.csv")
    parser.add_argument("-v", "--version", type=str, default="0.1")
    parser.add_argument(
        "--use-gpu", action="store_true", help="turn on flag to use GPU"
    )
    parser.add_argument("--dim", type=int, default="512")
    opt = parser.parse_args()
    use_gpu = opt.use_gpu
    dir_sources = opt.dir0
    dir_targets = opt.dir1
    dim = opt.dim
    ## Initializing the model
    loss_fn = lpips.LPIPS(net="alex", version=opt.version)
    if opt.use_gpu:
        loss_fn.cuda()
    IMGS = {}
    # crawl directories
    sources_files = [
        f
        for f in os.listdir(dir_sources)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"))
    ]
    target_files = [
        f
        for f in os.listdir(dir_targets)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"))
    ]
    begin = time.time()
    all_dists = []
    for source_file in sources_files:
        dists_cur = []
        source_img = os.path.join(dir_sources, source_file)
        assert os.path.exists(source_img)
        min_dist = float("inf")
        min_img_path = ""
        # Load images
        img0 = lpips.im2tensor(
            resize_image_keep_ratio_and_pad(cv2.imread(source_img), dim)
        )
        if use_gpu:
            img0 = img0.cuda()
        for target_file in target_files:
            target_img = os.path.join(dir_targets, target_file)
            assert os.path.exists(target_img)
            if target_img not in IMGS:
                img1 = lpips.im2tensor(
                    resize_image_keep_ratio_and_pad(cv2.imread(target_img), dim)
                )
                IMGS[target_img] = img1
            img1 = IMGS[target_img]
            if use_gpu:
                img1 = img1.cuda()
            # Compute distance
            dist = float(loss_fn.forward(img0, img1))
            if min_dist > dist:
                min_dist = dist
                min_img_path = target_img
            dists_cur.append(dist)
        all_dists.append(dists_cur)
        print(f"{source_file}: {min_dist:.3f} / {min_img_path}")
    elapsed = time.time() - begin
    len_src = len(sources_files)
    len_target = len(target_files)
    print(
        f"Total took : {elapsed} s, for sources size : {len_src} and targets size : {len_target}, i.e. {len_target*len_src} comparisons. This is {elapsed/(len_target*len_src)} s/pairs."
    )
    matrix = np.matrix(all_dists)
    df = pandas.DataFrame(matrix, columns=target_files, index=sources_files)
    print(df)
    df.to_csv(opt.out)
