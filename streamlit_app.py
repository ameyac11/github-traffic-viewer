import sys
from pathlib import Path

# Add the local package to the Python path
sys.path.append(str(Path(__file__).parent))

# Import the dashboard module to run the Streamlit app in the same process
import github_traffic.dashboard
