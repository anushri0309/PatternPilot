# test_garmentcode.py
from pygarment.data_config import Properties
from pygarment.garmentcode import Bodice

# Load default design parameters
props = Properties("assets/design_params/default.yaml")

# Create a basic bodice pattern
garment = Bodice(props)
garment.assert_valid()

# Save the pattern
garment.save("output/test_bodice")