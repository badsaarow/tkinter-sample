import open3d as o3d

def mesh_viewer(ply_file_path):
    # Read the .ply file
    mesh = o3d.io.read_triangle_mesh(ply_file_path)
    # Draw the mesh
    o3d.visualization.draw_geometries([mesh])
