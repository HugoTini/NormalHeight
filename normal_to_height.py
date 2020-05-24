import numpy as np


def normal_to_grad(normal_map):
    return (normal_map[0]-0.5)*2, (normal_map[1]-0.5)*2


def copy_flip(grad_x, grad_y):
    '''Concat 4 flipped copies of input gradients (makes them wrap). 
    Output is twice bigger in both dimensions.'''

    grad_x_top = np.hstack([grad_x, -np.flip(grad_x, axis=1)])
    grad_x_bottom = np.hstack([np.flip(grad_x, axis=0), -np.flip(grad_x)])
    new_grad_x = np.vstack([grad_x_top, grad_x_bottom])

    grad_y_top = np.hstack([grad_y, np.flip(grad_y, axis=1)])
    grad_y_bottom = np.hstack([-np.flip(grad_y, axis=0), -np.flip(grad_y)])
    new_grad_y = np.vstack([grad_y_top, grad_y_bottom])

    return new_grad_x, new_grad_y


def frankot_chellappa(grad_x, grad_y, normalize=True):
    '''Frankot-Chellappa depth-from-gradient algorithm.'''

    rows, cols = grad_x.shape

    rows_scale = (np.arange(rows)-(rows//2+1)) / (rows-rows % 2)
    cols_scale = (np.arange(cols)-(cols//2+1)) / (cols-cols % 2)

    u_grid, v_grid = np.meshgrid(cols_scale, rows_scale)

    u_grid = np.fft.ifftshift(u_grid)
    v_grid = np.fft.ifftshift(v_grid)

    grad_x_F = np.fft.fft2(grad_x)
    grad_y_F = np.fft.fft2(grad_y)

    nominator = (-1j*u_grid*grad_x_F) + (-1j*v_grid*grad_y_F)
    denominator = (u_grid**2) + (v_grid**2) + 1e-16

    Z_F = nominator / denominator
    Z_F[0, 0] = 0.0

    Z = np.real(np.fft.ifft2(Z_F))

    if normalize:
        return (Z-np.min(Z)) / (np.max(Z)-np.min(Z))

    return Z
