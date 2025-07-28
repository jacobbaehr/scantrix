import os

import open3d as o3d


def convert_ply_to_glb(ply_dir: os.PathLike, glb_dir: os.PathLike):
    # Load point cloud
    pcd = o3d.io.read_point_cloud(ply_dir)

    # Estimate normals — required for Poisson meshing
    pcd.estimate_normals()

    # Mesh from point cloud
    mesh, _ = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=9)

    # Optional: simplify the mesh to reduce size
    mesh = mesh.simplify_quadric_decimation(target_number_of_triangles=10000)

    # Save to GLB
    o3d.io.write_triangle_mesh(glb_dir, mesh)
