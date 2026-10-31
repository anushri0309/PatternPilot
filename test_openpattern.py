import matplotlib.pyplot as plt
import OpenPattern as OP
import os

# Ensure output folder exists
os.makedirs("output", exist_ok=True)

# Create the bodice
p = OP.Basic_Bodice(pname="W36G", gender='w', style='Gilewska')

# Add darts
p.add_bust_dart()
p.add_waist_dart()

# Draw and save
# save=True tells it to save, filename="output/test_bodice" tells it where
p.draw({"Pattern": "Test Bodice"}, save=True, filename="output/test_bodice")

print("✅ File saved to output/test_bodice")