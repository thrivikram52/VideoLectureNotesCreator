import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
import os
import argparse

def compare_images(image1_path, image2_path):
    # Read images
    img1 = cv2.imread(image1_path)
    img2 = cv2.imread(image2_path)

    # Convert images to grayscale
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    # Compute SSIM
    ssim_score, _ = ssim(gray1, gray2, full=True)

    # Initialize SIFT detector
    sift = cv2.SIFT_create()

    # Detect keypoints and compute descriptors
    kp1, des1 = sift.detectAndCompute(gray1, None)
    kp2, des2 = sift.detectAndCompute(gray2, None)

    # Match keypoints
    bf = cv2.BFMatcher()
    matches = bf.knnMatch(des1, des2, k=2)

    # Apply ratio test
    good_matches = []
    for m, n in matches:
        if m.distance < 0.75 * n.distance:
            good_matches.append(m)

    # Compute similarity metrics
    num_good_matches = len(good_matches)
    min_keypoints = min(len(kp1), len(kp2))
    good_matches_ratio = num_good_matches / min_keypoints if min_keypoints > 0 else 0

    # Print results
    print(f"Comparing: {os.path.basename(image1_path)} and {os.path.basename(image2_path)}")
    print(f"SSIM Score: {ssim_score:.4f}")
    print(f"Number of keypoints in image 1: {len(kp1)}")
    print(f"Number of keypoints in image 2: {len(kp2)}")
    print(f"Number of good matches: {num_good_matches}")
    print(f"Good matches ratio: {good_matches_ratio:.4f}")

    # Visualize matches
    img_matches = cv2.drawMatches(img1, kp1, img2, kp2, good_matches, None, flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
    cv2.imshow("Matches", img_matches)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare two images from the scenes folder")
    parser.add_argument("image1", help="Filename of the first image in the scenes folder")
    parser.add_argument("image2", help="Filename of the second image in the scenes folder")
    args = parser.parse_args()

    scenes_folder = 'scenes'
    
    image1_path = os.path.join(scenes_folder, args.image1)
    image2_path = os.path.join(scenes_folder, args.image2)
    
    if not os.path.exists(image1_path) or not os.path.exists(image2_path):
        print("Error: One or both of the specified images do not exist in the scenes folder.")
    else:
        compare_images(image1_path, image2_path)
