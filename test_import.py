import torch, torchvision, cv2, numpy as np
import PIL
import einops, skimage, kornia
print("torch:", torch.__version__, "cuda?", torch.cuda.is_available())
print("opencv:", cv2.__version__)
print("Pillow:", PIL.__version__)
print("numpy:", np.__version__)
print("ALL_OK")
