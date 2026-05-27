import plotly.express as px
import pandas as pd
import numpy as np

# Simulate the 120D Composition Space projected to 3D for the video
np.random.seed(42)
n_materials = 200
data = {
    'Component 1': np.random.randn(n_materials),
    'Component 2': np.random.randn(n_materials),
    'Component 3': np.random.randn(n_materials),
    'Material Class': np.random.choice(['Battery', 'Ceramic', 'Polymer', 'Metal'], n_materials),
    'Synthesizability': np.random.rand(n_materials)
}

df = pd.DataFrame(data)

fig = px.scatter_3d(
    df, x='Component 1', y='Component 2', z='Component 3',
    color='Material Class', size='Synthesizability',
    title="KOMPOSOS-IV: 120D Physics-Embedded Composition Space (Projection)",
    template="plotly_dark"
)

fig.update_layout(scene=dict(xaxis_showspikes=False, yaxis_showspikes=False, zaxis_showspikes=False))
fig.show()

# INSTRUCTIONS: Run this snippet to generate an interactive 3D visual for the video background.
