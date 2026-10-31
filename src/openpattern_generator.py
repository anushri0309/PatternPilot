import OpenPattern as OP
import os


class OpenPatternGenerator:
    def __init__(self, spec):
        self.spec = spec

    def generate(self, output_prefix):
        gender = 'w'
        if 'male' in self.spec.get('gender', '').lower():
            gender = 'm'

        gtype = self.spec['garment_type'].lower()

        try:
            if 'dress' in gtype or 'top' in gtype or 'shirt' in gtype:
                pattern = OP.Basic_Bodice(pname="W36G", gender=gender, style='Gilewska')
            elif 'skirt' in gtype:
                pattern = OP.Basic_Skirt(pname="W36G", gender=gender, style='Gilewska')
            elif 'pants' in gtype or 'jeans' in gtype:
                pattern = OP.Trouser(pname="W36G", gender=gender, style='Gilewska')
            else:
                pattern = OP.Basic_Bodice(pname="W36G", gender=gender, style='Gilewska')
        except Exception as e:
            print(f"❌ OpenPattern could not create the garment: {e}")
            return False

        print(f"✅ OpenPattern using standard size W36G (Gilewska)")

        # 1. Save current directory
        original_dir = os.getcwd()

        # 2. Ensure output folder exists, and change into it
        os.makedirs("output", exist_ok=True)
        os.chdir("output")

        try:
            print(f"🎨 Drawing OpenPattern into /output folder...")
            # This will now save the PDF directly inside the output folder
            pattern.draw({"Pattern": self.spec['garment_type']}, save=True)
            print(f"✅ OpenPattern saved successfully inside the output folder!")
        except Exception as e:
            print(f"⚠️ Error drawing OpenPattern: {e}")
        finally:
            # 3. Change directory back to the root
            os.chdir(original_dir)

        return True