"""Generate photorealistic simulated test bills to complete the 12-bill test suite."""

import math
import os
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

BILLS_DIR = Path(r"c:\Users\nehab\OneDrive\Desktop\BillSplit\billsplit-ai\test_data\bills")
BILLS_DIR.mkdir(parents=True, exist_ok=True)

FONTS_DIR = Path(r"C:\Windows\Fonts")
CONSOLA = str(FONTS_DIR / "consola.ttf")
CONSOLAB = str(FONTS_DIR / "consolab.ttf")
NIRMALA = str(FONTS_DIR / "nirmala.ttc")
SEGOEPR = str(FONTS_DIR / "segoepr.ttf")
ARIAL = str(FONTS_DIR / "arial.ttf")
ARIALBD = str(FONTS_DIR / "arialbd.ttf")


def add_paper_texture(img, bg_color=(250, 249, 246), noise_intensity=12):
    """Add subtle paper texture and slight grain."""
    w, h = img.size
    overlay = Image.new("RGB", (w, h), bg_color)
    draw = ImageDraw.Draw(overlay)
    random.seed(42)
    for _ in range(w * h // 30):
        x = random.randint(0, w - 1)
        y = random.randint(0, h - 1)
        val = random.randint(-noise_intensity, noise_intensity)
        c = (max(0, min(255, bg_color[0] + val)),
             max(0, min(255, bg_color[1] + val)),
             max(0, min(255, bg_color[2] + val)))
        draw.point((x, y), fill=c)
    return Image.blend(overlay, img, 0.9)


def render_bill_03_long():
    """bill_03_long.png: Long restaurant bill with 16 line items."""
    w, h = 600, 1150
    img = Image.new("RGB", (w, h), (252, 250, 245))
    draw = ImageDraw.Draw(img)
    f_title = ImageFont.truetype(CONSOLAB, 22)
    f_sub = ImageFont.truetype(CONSOLA, 14)
    f_body = ImageFont.truetype(CONSOLA, 15)
    f_bold = ImageFont.truetype(CONSOLAB, 15)

    y = 30
    draw.text((w // 2, y), "BARBEQUE NATION HOSPITALITY", font=f_title, fill=(20, 20, 20), anchor="mt")
    y += 26
    draw.text((w // 2, y), "3rd Floor, Phoenix Marketcity, Kurla, Mumbai", font=f_sub, fill=(60, 60, 60), anchor="mt")
    y += 20
    draw.text((w // 2, y), "GSTIN: 27AABCB1234F1Z9 | Ph: 022-61801234", font=f_sub, fill=(60, 60, 60), anchor="mt")
    y += 20
    draw.text((w // 2, y), "Date: 14-Aug-2023 21:30 | Table: T-14 | Covers: 4", font=f_sub, fill=(60, 60, 60), anchor="mt")
    y += 20
    draw.text((w // 2, y), "-" * 56, font=f_sub, fill=(80, 80, 80), anchor="mt")
    y += 18
    # Header row
    draw.text((25, y), "ITEM", font=f_bold, fill=(20, 20, 20))
    draw.text((360, y), "QTY", font=f_bold, fill=(20, 20, 20))
    draw.text((430, y), "RATE", font=f_bold, fill=(20, 20, 20))
    draw.text((575, y), "TOTAL", font=f_bold, fill=(20, 20, 20), anchor="ra")
    y += 20
    draw.text((w // 2, y), "-" * 56, font=f_sub, fill=(80, 80, 80), anchor="mt")
    y += 16

    items = [
        ("Veg Crispy Corn", 2, 180.0, 360.0),
        ("Cajun Spiced Potato", 1, 210.0, 210.0),
        ("Paneer Tikka Shashlik", 2, 290.0, 580.0),
        ("Chicken Tangdi Kebab", 2, 340.0, 680.0),
        ("Mutton Seekh Kebab", 1, 390.0, 390.0),
        ("Fish Amritsari", 1, 380.0, 380.0),
        ("Dal Makhani", 2, 240.0, 480.0),
        ("Paneer Butter Masala", 1, 320.0, 320.0),
        ("Butter Chicken", 2, 380.0, 760.0),
        ("Garlic Naan", 6, 60.0, 360.0),
        ("Butter Roti", 4, 35.0, 140.0),
        ("Jeera Rice", 2, 160.0, 320.0),
        ("Gulab Jamun with Ice Cream", 4, 110.0, 440.0),
        ("Chocolate Brownie", 2, 150.0, 300.0),
        ("Fresh Lime Soda", 3, 80.0, 240.0),
        ("Virgin Mojito", 2, 140.0, 280.0),
    ]

    for name, qty, rate, total in items:
        draw.text((25, y), name, font=f_body, fill=(30, 30, 30))
        draw.text((370, y), str(qty), font=f_body, fill=(30, 30, 30))
        draw.text((430, y), f"{rate:.2f}", font=f_body, fill=(30, 30, 30))
        draw.text((575, y), f"{total:.2f}", font=f_body, fill=(30, 30, 30), anchor="ra")
        y += 24

    draw.text((w // 2, y), "-" * 56, font=f_sub, fill=(80, 80, 80), anchor="mt")
    y += 18
    # Subtotal
    subtotal = sum(t for _, _, _, t in items)  # 6240.00
    draw.text((25, y), "Sub Total", font=f_bold, fill=(20, 20, 20))
    draw.text((575, y), f"{subtotal:.2f}", font=f_bold, fill=(20, 20, 20), anchor="ra")
    y += 24
    cgst = 156.00  # 2.5% of 6240
    sgst = 156.00  # 2.5% of 6240
    tax = cgst + sgst
    draw.text((25, y), "CGST @ 2.5%", font=f_body, fill=(40, 40, 40))
    draw.text((575, y), f"{cgst:.2f}", font=f_body, fill=(40, 40, 40), anchor="ra")
    y += 22
    draw.text((25, y), "SGST @ 2.5%", font=f_body, fill=(40, 40, 40))
    draw.text((575, y), f"{sgst:.2f}", font=f_body, fill=(40, 40, 40), anchor="ra")
    y += 22
    sc = 312.00  # Service Charge 5%
    draw.text((25, y), "Service Charge @ 5.0%", font=f_body, fill=(40, 40, 40))
    draw.text((575, y), f"{sc:.2f}", font=f_body, fill=(40, 40, 40), anchor="ra")
    y += 22
    draw.text((w // 2, y), "=" * 56, font=f_sub, fill=(60, 60, 60), anchor="mt")
    y += 20
    grand_total = subtotal + tax + sc  # 6864.00
    draw.text((25, y), "GRAND TOTAL (INR)", font=ImageFont.truetype(CONSOLAB, 18), fill=(10, 10, 10))
    draw.text((575, y), f"₹ {grand_total:.2f}", font=ImageFont.truetype(CONSOLAB, 18), fill=(10, 10, 10), anchor="ra")
    y += 30
    draw.text((w // 2, y), "*** THANK YOU FOR DINING WITH US ***", font=f_sub, fill=(60, 60, 60), anchor="mt")

    img = add_paper_texture(img, bg_color=(250, 248, 242))
    img.save(BILLS_DIR / "bill_03_long.png")
    print("Saved bill_03_long.png")


def render_bill_06_angled():
    """bill_06_angled.png: Bill photographed at a steep 45° angle on a desk."""
    # First create flat receipt
    w, h = 500, 650
    flat = Image.new("RGB", (w, h), (252, 252, 250))
    draw = ImageDraw.Draw(flat)
    f_title = ImageFont.truetype(CONSOLAB, 20)
    f_sub = ImageFont.truetype(CONSOLA, 13)
    f_body = ImageFont.truetype(CONSOLA, 14)
    f_bold = ImageFont.truetype(CONSOLAB, 15)

    y = 25
    draw.text((w // 2, y), "SARAVANAA BHAVAN", font=f_title, fill=(20, 20, 20), anchor="mt")
    y += 25
    draw.text((w // 2, y), "Connaught Place, New Delhi", font=f_sub, fill=(50, 50, 50), anchor="mt")
    y += 18
    draw.text((w // 2, y), "Date: 19/09/2023 | Bill No: 4892", font=f_sub, fill=(50, 50, 50), anchor="mt")
    y += 18
    draw.text((w // 2, y), "-" * 48, font=f_sub, fill=(80, 80, 80), anchor="mt")
    y += 18

    items = [
        ("Ghee Roast Dosa", 1, 140.0, 140.0),
        ("Rava Masala Dosa", 1, 160.0, 160.0),
        ("Medu Vada (2 Pcs)", 2, 90.0, 180.0),
        ("Filter Coffee", 3, 50.0, 150.0),
        ("Mini Tiffin Thali", 1, 220.0, 220.0),
    ]

    for name, qty, rate, total in items:
        draw.text((25, y), name, font=f_body, fill=(30, 30, 30))
        draw.text((320, y), str(qty), font=f_body, fill=(30, 30, 30))
        draw.text((380, y), f"{rate:.0f}", font=f_body, fill=(30, 30, 30))
        draw.text((475, y), f"{total:.0f}", font=f_body, fill=(30, 30, 30), anchor="ra")
        y += 24

    draw.text((w // 2, y), "-" * 48, font=f_sub, fill=(80, 80, 80), anchor="mt")
    y += 18
    subtotal = 850.00
    cgst = 21.25
    sgst = 21.25
    total = 892.50
    draw.text((25, y), "Subtotal", font=f_bold, fill=(20, 20, 20))
    draw.text((475, y), f"{subtotal:.2f}", font=f_bold, fill=(20, 20, 20), anchor="ra")
    y += 22
    draw.text((25, y), "CGST 2.5%", font=f_body, fill=(40, 40, 40))
    draw.text((475, y), f"{cgst:.2f}", font=f_body, fill=(40, 40, 40), anchor="ra")
    y += 20
    draw.text((25, y), "SGST 2.5%", font=f_body, fill=(40, 40, 40))
    draw.text((475, y), f"{sgst:.2f}", font=f_body, fill=(40, 40, 40), anchor="ra")
    y += 22
    draw.text((w // 2, y), "=" * 48, font=f_sub, fill=(60, 60, 60), anchor="mt")
    y += 20
    draw.text((25, y), "NET PAYABLE", font=ImageFont.truetype(CONSOLAB, 17), fill=(10, 10, 10))
    draw.text((475, y), f"₹ {total:.2f}", font=ImageFont.truetype(CONSOLAB, 17), fill=(10, 10, 10), anchor="ra")

    # Now apply perspective transformation onto a dark wood/slate tabletop
    bg_w, bg_h = 750, 750
    canvas = Image.new("RGB", (bg_w, bg_h), (55, 42, 35))  # Dark wood tone
    # Add wood grain
    cdraw = ImageDraw.Draw(canvas)
    for row in range(0, bg_h, 4):
        shade = 55 + (row % 12) * 2
        cdraw.line([(0, row), (bg_w, row)], fill=(shade, shade - 15, shade - 20))

    # Compute 3D projective transform for steep 45° perspective
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    # Top narrower and receded, bottom wider and closer
    dst = [(220, 80), (530, 130), (590, 680), (120, 630)]

    def find_coeffs(pa, pb):
        matrix = []
        for p1, p2 in zip(pa, pb):
            matrix.append([p1[0], p1[1], 1, 0, 0, 0, -p2[0]*p1[0], -p2[0]*p1[1], p2[0]])
            matrix.append([0, 0, 0, p1[0], p1[1], 1, -p2[1]*p1[0], -p2[1]*p1[1], p2[1]])
        # Solve 8x8 linear system via Gaussian elimination
        n = 8
        for i in range(n):
            max_row = max(range(i, n), key=lambda r: abs(matrix[r][i]))
            matrix[i], matrix[max_row] = matrix[max_row], matrix[i]
            pivot = matrix[i][i]
            for j in range(i, n + 1):
                matrix[i][j] /= pivot
            for k in range(n):
                if k != i:
                    factor = matrix[k][i]
                    for j in range(i, n + 1):
                        matrix[k][j] -= factor * matrix[i][j]
        return [matrix[i][n] for i in range(n)]

    coeffs = find_coeffs(dst, src)
    warped = flat.transform((bg_w, bg_h), Image.PERSPECTIVE, coeffs, Image.BICUBIC)
    # Mask
    mask = Image.new("L", (w, h), 255)
    warped_mask = mask.transform((bg_w, bg_h), Image.PERSPECTIVE, coeffs, Image.BICUBIC)

    # Shadow under receipt
    shadow = warped_mask.filter(ImageFilter.GaussianBlur(15))
    canvas.paste((20, 15, 12), (0, 0), shadow)
    canvas.paste(warped, (0, 0), warped_mask)

    canvas.save(BILLS_DIR / "bill_06_angled.png")
    print("Saved bill_06_angled.png")


def render_bill_07_thermal_faded():
    """bill_07_thermal_faded.png: Faded thermal print with low contrast and washed-out print."""
    w, h = 500, 650
    img = Image.new("RGB", (w, h), (242, 238, 228))  # Aged yellowish thermal paper
    draw = ImageDraw.Draw(img)
    f_title = ImageFont.truetype(CONSOLA, 18)
    f_body = ImageFont.truetype(CONSOLA, 14)

    # Pale grey ink (washed out thermal print)
    ink = (135, 132, 125)
    faint_ink = (155, 152, 145)

    y = 30
    draw.text((w // 2, y), "NATURE'S BASKET LTD", font=f_title, fill=ink, anchor="mt")
    y += 24
    draw.text((w // 2, y), "Bandra West, Mumbai 400050", font=f_body, fill=faint_ink, anchor="mt")
    y += 18
    draw.text((w // 2, y), "TAX INVOICE / POS CASH", font=f_body, fill=faint_ink, anchor="mt")
    y += 20
    draw.text((w // 2, y), "- - - - - - - - - - - - - - - - - - - -", font=f_body, fill=faint_ink, anchor="mt")
    y += 18

    items = [
        ("Epigamia Greek Yogurt", 2, 80.0, 160.0),
        ("Sourdough Bread Loaf", 1, 140.0, 140.0),
        ("Avocado Hass Imported", 2, 125.0, 250.0),
        ("Almond Milk 1 Litre", 1, 290.0, 290.0),
        ("Organic Baby Spinach", 1, 65.0, 65.0),
    ]

    for name, qty, rate, total in items:
        # Fade effect: top of letters slightly lighter
        draw.text((25, y), name, font=f_body, fill=ink)
        draw.text((310, y), str(qty), font=f_body, fill=ink)
        draw.text((365, y), f"{rate:.0f}", font=f_body, fill=ink)
        draw.text((475, y), f"{total:.0f}", font=f_body, fill=ink, anchor="ra")
        y += 24

    draw.text((w // 2, y), "- - - - - - - - - - - - - - - - - - - -", font=f_body, fill=faint_ink, anchor="mt")
    y += 18
    subtotal = 905.00
    gst = 45.25  # 5% composite GST
    total = 950.25
    draw.text((25, y), "SUBTOTAL", font=f_body, fill=ink)
    draw.text((475, y), f"{subtotal:.2f}", font=f_body, fill=ink, anchor="ra")
    y += 22
    draw.text((25, y), "GST (5.0%)", font=f_body, fill=faint_ink)
    draw.text((475, y), f"{gst:.2f}", font=f_body, fill=faint_ink, anchor="ra")
    y += 22
    draw.text((w // 2, y), "= = = = = = = = = = = = = = = = = = = =", font=f_body, fill=faint_ink, anchor="mt")
    y += 20
    draw.text((25, y), "TOTAL AMOUNT", font=f_title, fill=ink)
    draw.text((475, y), f"INR {total:.2f}", font=f_title, fill=ink, anchor="ra")

    # Add thermal printer head streaks (horizontal faint white bands)
    for band_y in range(120, h - 50, 45):
        draw.line([(0, band_y), (w, band_y)], fill=(245, 242, 235), width=2)

    img = add_paper_texture(img, bg_color=(240, 237, 226), noise_intensity=18)
    # Slight blur to simulate thermal spread
    img = img.filter(ImageFilter.GaussianBlur(0.4))
    img.save(BILLS_DIR / "bill_07_thermal_faded.png")
    print("Saved bill_07_thermal_faded.png")


def render_bill_08_handwritten():
    """bill_08_handwritten.png: Printed bill with ballpoint pen handwriting additions and checks."""
    w, h = 520, 680
    img = Image.new("RGB", (w, h), (252, 252, 250))
    draw = ImageDraw.Draw(img)
    f_title = ImageFont.truetype(CONSOLAB, 20)
    f_body = ImageFont.truetype(CONSOLA, 15)
    f_sub = ImageFont.truetype(CONSOLA, 13)
    f_pen = ImageFont.truetype(SEGOEPR, 16)  # Authentic handwriting font

    y = 25
    draw.text((w // 2, y), "MAINLAND CHINA", font=f_title, fill=(20, 20, 20), anchor="mt")
    y += 25
    draw.text((w // 2, y), "Andheri West, Mumbai", font=f_sub, fill=(60, 60, 60), anchor="mt")
    y += 18
    draw.text((w // 2, y), "Table: 06 | Date: 05-Nov-2023", font=f_sub, fill=(60, 60, 60), anchor="mt")
    y += 18
    draw.text((w // 2, y), "-" * 50, font=f_sub, fill=(80, 80, 80), anchor="mt")
    y += 18

    items = [
        ("Chicken Sui Mai", 1, 340.0, 340.0),
        ("Crispy Chilli Corn", 1, 290.0, 290.0),
        ("Hakka Noodles", 2, 260.0, 520.0),
        ("Kung Pao Chicken", 1, 410.0, 410.0),
        ("Jasmine Green Tea", 2, 110.0, 220.0),
    ]

    blue_pen = (25, 45, 140)

    for name, qty, rate, total in items:
        draw.text((35, y), name, font=f_body, fill=(30, 30, 30))
        draw.text((330, y), str(qty), font=f_body, fill=(30, 30, 30))
        draw.text((390, y), f"{rate:.0f}", font=f_body, fill=(30, 30, 30))
        draw.text((495, y), f"{total:.0f}", font=f_body, fill=(30, 30, 30), anchor="ra")
        # Pen checkmark next to item
        draw.text((15, y - 2), "✓", font=f_pen, fill=blue_pen)
        y += 26

    draw.text((w // 2, y), "-" * 50, font=f_sub, fill=(80, 80, 80), anchor="mt")
    y += 18
    subtotal = 1780.00
    cgst = 44.50
    sgst = 44.50
    sc = 89.00  # 5% Service Charge
    total = 1958.00

    draw.text((35, y), "Subtotal", font=f_body, fill=(20, 20, 20))
    draw.text((495, y), f"{subtotal:.2f}", font=f_body, fill=(20, 20, 20), anchor="ra")
    y += 22
    draw.text((35, y), "CGST 2.5%", font=f_body, fill=(40, 40, 40))
    draw.text((495, y), f"{cgst:.2f}", font=f_body, fill=(40, 40, 40), anchor="ra")
    y += 22
    draw.text((35, y), "SGST 2.5%", font=f_body, fill=(40, 40, 40))
    draw.text((495, y), f"{sgst:.2f}", font=f_body, fill=(40, 40, 40), anchor="ra")
    y += 22
    draw.text((35, y), "Service Charge 5%", font=f_body, fill=(40, 40, 40))
    draw.text((495, y), f"{sc:.2f}", font=f_body, fill=(40, 40, 40), anchor="ra")
    y += 22
    draw.text((w // 2, y), "=" * 50, font=f_sub, fill=(60, 60, 60), anchor="mt")
    y += 20
    draw.text((35, y), "BILL TOTAL", font=ImageFont.truetype(CONSOLAB, 17), fill=(10, 10, 10))
    draw.text((495, y), f"₹ {total:.2f}", font=ImageFont.truetype(CONSOLAB, 17), fill=(10, 10, 10), anchor="ra")

    # Pen annotations: circle around total, tip note "+ ₹100 tip = 2058", signature
    draw.ellipse([(360, y - 5), (510, y + 26)], outline=blue_pen, width=2)
    y += 35
    draw.text((35, y), "Tip: + Rs. 100/- (Paid Cash)", font=f_pen, fill=blue_pen)
    y += 26
    draw.text((35, y), "Total Paid = 2058/-  [N. Sharma]", font=f_pen, fill=blue_pen)

    img = add_paper_texture(img, bg_color=(250, 249, 246))
    img.save(BILLS_DIR / "bill_08_handwritten.png")
    print("Saved bill_08_handwritten.png")


def render_bill_09_two_scripts():
    """bill_09_two_scripts.png: Bilingual receipt in Devanagari Hindi and English."""
    w, h = 560, 680
    img = Image.new("RGB", (w, h), (252, 252, 249))
    draw = ImageDraw.Draw(img)
    f_title_hi = ImageFont.truetype(NIRMALA, 22)
    f_title_en = ImageFont.truetype(ARIALBD, 15)
    f_sub = ImageFont.truetype(NIRMALA, 13)
    f_item_hi = ImageFont.truetype(NIRMALA, 14)
    f_item_en = ImageFont.truetype(ARIAL, 12)
    f_num = ImageFont.truetype(CONSOLA, 14)
    f_bold = ImageFont.truetype(ARIALBD, 14)

    y = 25
    draw.text((w // 2, y), "हल्दीराम भुजियावाला / HALDIRAM", font=f_title_hi, fill=(20, 20, 20), anchor="mt")
    y += 30
    draw.text((w // 2, y), "कनॉट प्लेस, नई दिल्ली / Connaught Place, New Delhi", font=f_sub, fill=(60, 60, 60), anchor="mt")
    y += 20
    draw.text((w // 2, y), "बिल सं. / Bill No: 1042 | दिनांक / Date: 12-10-2023", font=f_sub, fill=(60, 60, 60), anchor="mt")
    y += 20
    draw.line([(25, y), (w - 25, y)], fill=(120, 120, 120), width=1)
    y += 10

    # Table Header
    draw.text((25, y), "विवरण / Item", font=f_bold, fill=(20, 20, 20))
    draw.text((330, y), "मात्रा/Qty", font=f_bold, fill=(20, 20, 20))
    draw.text((410, y), "दर/Rate", font=f_bold, fill=(20, 20, 20))
    draw.text((535, y), "योग/Total", font=f_bold, fill=(20, 20, 20), anchor="ra")
    y += 22
    draw.line([(25, y), (w - 25, y)], fill=(120, 120, 120), width=1)
    y += 10

    items = [
        ("छोले भटूरे / Chole Bhature", 2, 160.0, 320.0),
        ("राज कचौरी / Raj Kachori", 1, 130.0, 130.0),
        ("पाव भाजी / Pav Bhaji", 2, 150.0, 300.0),
        ("गुलाब जामुन / Gulab Jamun", 4, 40.0, 160.0),
        ("केसर लस्सी / Kesar Lassi", 2, 90.0, 180.0),
    ]

    for name, qty, rate, total in items:
        draw.text((25, y), name, font=f_item_hi, fill=(30, 30, 30))
        draw.text((345, y), str(qty), font=f_num, fill=(30, 30, 30))
        draw.text((415, y), f"{rate:.0f}", font=f_num, fill=(30, 30, 30))
        draw.text((535, y), f"{total:.2f}", font=f_num, fill=(30, 30, 30), anchor="ra")
        y += 26

    draw.line([(25, y), (w - 25, y)], fill=(120, 120, 120), width=1)
    y += 14
    subtotal = 1090.00
    cgst = 27.25
    sgst = 27.25
    total = 1144.50

    draw.text((25, y), "उप-योग / Sub Total", font=f_item_hi, fill=(20, 20, 20))
    draw.text((535, y), f"₹ {subtotal:.2f}", font=f_num, fill=(20, 20, 20), anchor="ra")
    y += 24
    draw.text((25, y), "सीजीएसटी / CGST @ 2.5%", font=f_item_hi, fill=(50, 50, 50))
    draw.text((535, y), f"₹ {cgst:.2f}", font=f_num, fill=(50, 50, 50), anchor="ra")
    y += 22
    draw.text((25, y), "एसजीएसटी / SGST @ 2.5%", font=f_item_hi, fill=(50, 50, 50))
    draw.text((535, y), f"₹ {sgst:.2f}", font=f_num, fill=(50, 50, 50), anchor="ra")
    y += 24
    draw.line([(25, y), (w - 25, y)], fill=(80, 80, 80), width=2)
    y += 12
    draw.text((25, y), "कुल देय / Net Amount", font=ImageFont.truetype(NIRMALA, 16), fill=(10, 10, 10))
    draw.text((535, y), f"₹ {total:.2f}", font=ImageFont.truetype(CONSOLAB, 17), fill=(10, 10, 10), anchor="ra")

    img = add_paper_texture(img, bg_color=(250, 248, 242))
    img.save(BILLS_DIR / "bill_09_two_scripts.png")
    print("Saved bill_09_two_scripts.png")


def render_bill_10_two_photos():
    """bill_10a.png & bill_10b.png: Two-photo long bill for stitched multi-photo extraction."""
    w, h = 550, 600
    f_title = ImageFont.truetype(CONSOLAB, 20)
    f_sub = ImageFont.truetype(CONSOLA, 13)
    f_body = ImageFont.truetype(CONSOLA, 14)
    f_bold = ImageFont.truetype(CONSOLAB, 15)

    all_items = [
        ("Tomato Shorba", 2, 140.0, 280.0),
        ("Hara Bhara Kebab", 2, 220.0, 440.0),
        ("Paneer Malai Tikka", 1, 310.0, 310.0),
        ("Chicken Seekh Kebab", 2, 350.0, 700.0),
        ("Crispy Corn Chaat", 1, 190.0, 190.0),
        ("Butter Chicken Masala", 2, 390.0, 780.0),
        ("Dal Tadka", 1, 210.0, 210.0),
        # Split point here
        ("Kadhai Paneer", 1, 320.0, 320.0),
        ("Garlic Naan", 4, 65.0, 260.0),
        ("Tandoori Roti", 6, 30.0, 180.0),
        ("Steamed Basmati Rice", 2, 140.0, 280.0),
        ("Gulab Jamun (2 pcs)", 2, 90.0, 180.0),
        ("Sweet Lassi", 3, 80.0, 240.0),
        ("Mineral Water", 2, 35.0, 70.0),
    ]

    # Photo A (Top Half)
    img_a = Image.new("RGB", (w, h), (252, 250, 246))
    draw_a = ImageDraw.Draw(img_a)
    y = 25
    draw_a.text((w // 2, y), "PUNJAB GRILL", font=f_title, fill=(20, 20, 20), anchor="mt")
    y += 24
    draw_a.text((w // 2, y), "Ambience Mall, Gurugram, Haryana", font=f_sub, fill=(60, 60, 60), anchor="mt")
    y += 18
    draw_a.text((w // 2, y), "Invoice: PG-8821 | Date: 28/11/2023 20:15", font=f_sub, fill=(60, 60, 60), anchor="mt")
    y += 18
    draw_a.text((w // 2, y), "[ PART 1 OF 2 ]", font=f_bold, fill=(100, 100, 100), anchor="mt")
    y += 20
    draw_a.text((w // 2, y), "-" * 52, font=f_sub, fill=(80, 80, 80), anchor="mt")
    y += 18
    draw_a.text((25, y), "ITEM", font=f_bold, fill=(20, 20, 20))
    draw_a.text((330, y), "QTY", font=f_bold, fill=(20, 20, 20))
    draw_a.text((400, y), "RATE", font=f_bold, fill=(20, 20, 20))
    draw_a.text((525, y), "TOTAL", font=f_bold, fill=(20, 20, 20), anchor="ra")
    y += 22
    draw_a.text((w // 2, y), "-" * 52, font=f_sub, fill=(80, 80, 80), anchor="mt")
    y += 18

    for name, qty, rate, total in all_items[:7]:
        draw_a.text((25, y), name, font=f_body, fill=(30, 30, 30))
        draw_a.text((340, y), str(qty), font=f_body, fill=(30, 30, 30))
        draw_a.text((405, y), f"{rate:.0f}", font=f_body, fill=(30, 30, 30))
        draw_a.text((525, y), f"{total:.2f}", font=f_body, fill=(30, 30, 30), anchor="ra")
        y += 26

    draw_a.text((w // 2, y + 20), "-- Continued on next page --", font=f_sub, fill=(120, 120, 120), anchor="mt")
    img_a = add_paper_texture(img_a)
    img_a.save(BILLS_DIR / "bill_10a.png")
    print("Saved bill_10a.png")

    # Photo B (Bottom Half)
    img_b = Image.new("RGB", (w, h), (252, 250, 246))
    draw_b = ImageDraw.Draw(img_b)
    y = 25
    draw_b.text((w // 2, y), "PUNJAB GRILL (Contd...)", font=f_bold, fill=(20, 20, 20), anchor="mt")
    y += 20
    draw_b.text((w // 2, y), "[ PART 2 OF 2 ]", font=f_sub, fill=(100, 100, 100), anchor="mt")
    y += 20
    draw_b.text((w // 2, y), "-" * 52, font=f_sub, fill=(80, 80, 80), anchor="mt")
    y += 18

    for name, qty, rate, total in all_items[7:]:
        draw_b.text((25, y), name, font=f_body, fill=(30, 30, 30))
        draw_b.text((340, y), str(qty), font=f_body, fill=(30, 30, 30))
        draw_b.text((405, y), f"{rate:.0f}", font=f_body, fill=(30, 30, 30))
        draw_b.text((525, y), f"{total:.2f}", font=f_body, fill=(30, 30, 30), anchor="ra")
        y += 26

    draw_b.text((w // 2, y), "-" * 52, font=f_sub, fill=(80, 80, 80), anchor="mt")
    y += 18
    subtotal = sum(t for _, _, _, t in all_items)  # 4440.00
    cgst = 111.00  # 2.5%
    sgst = 111.00  # 2.5%
    total = subtotal + cgst + sgst  # 4662.00

    draw_b.text((25, y), "Subtotal", font=f_bold, fill=(20, 20, 20))
    draw_b.text((525, y), f"{subtotal:.2f}", font=f_bold, fill=(20, 20, 20), anchor="ra")
    y += 22
    draw_b.text((25, y), "CGST @ 2.5%", font=f_body, fill=(40, 40, 40))
    draw_b.text((525, y), f"{cgst:.2f}", font=f_body, fill=(40, 40, 40), anchor="ra")
    y += 22
    draw_b.text((25, y), "SGST @ 2.5%", font=f_body, fill=(40, 40, 40))
    draw_b.text((525, y), f"{sgst:.2f}", font=f_body, fill=(40, 40, 40), anchor="ra")
    y += 22
    draw_b.text((w // 2, y), "=" * 52, font=f_sub, fill=(60, 60, 60), anchor="mt")
    y += 20
    draw_b.text((25, y), "TOTAL PAYABLE", font=ImageFont.truetype(CONSOLAB, 17), fill=(10, 10, 10))
    draw_b.text((525, y), f"INR {total:.2f}", font=ImageFont.truetype(CONSOLAB, 17), fill=(10, 10, 10), anchor="ra")
    y += 30
    draw_b.text((w // 2, y), "Thank You! Visit Again", font=f_sub, fill=(60, 60, 60), anchor="mt")

    img_b = add_paper_texture(img_b)
    img_b.save(BILLS_DIR / "bill_10b.png")
    print("Saved bill_10b.png")


def render_bill_11_shared_heavy():
    """bill_11_shared_heavy.png: Shared-item-heavy bill with group platters and beverage pitchers."""
    w, h = 540, 680
    img = Image.new("RGB", (w, h), (252, 252, 248))
    draw = ImageDraw.Draw(img)
    f_title = ImageFont.truetype(CONSOLAB, 20)
    f_sub = ImageFont.truetype(CONSOLA, 13)
    f_body = ImageFont.truetype(CONSOLA, 14)
    f_bold = ImageFont.truetype(CONSOLAB, 15)

    y = 25
    draw.text((w // 2, y), "THE BEER CAFE", font=f_title, fill=(20, 20, 20), anchor="mt")
    y += 24
    draw.text((w // 2, y), "Cyber Hub, DLF Phase 2, Gurugram", font=f_sub, fill=(60, 60, 60), anchor="mt")
    y += 18
    draw.text((w // 2, y), "Table: High-Top 4 | Guests: 5 | 16-Sep-2023", font=f_sub, fill=(60, 60, 60), anchor="mt")
    y += 18
    draw.text((w // 2, y), "-" * 50, font=f_sub, fill=(80, 80, 80), anchor="mt")
    y += 18

    # Specific shared items designed for subsets of 2 or 3 people
    items = [
        ("Kingfisher Draught Pitcher", 2, 750.0, 1500.0),
        ("Loaded Nachos Platter", 1, 420.0, 420.0),
        ("Non-Veg Kebab Platter", 1, 850.0, 850.0),
        ("Margherita Pizza 12inch", 1, 480.0, 480.0),
        ("BBQ Chicken Wings (12pcs)", 1, 520.0, 520.0),
        ("Cheesy Garlic Bread", 2, 190.0, 380.0),
    ]

    for name, qty, rate, total in items:
        draw.text((25, y), name, font=f_body, fill=(30, 30, 30))
        draw.text((330, y), str(qty), font=f_body, fill=(30, 30, 30))
        draw.text((395, y), f"{rate:.0f}", font=f_body, fill=(30, 30, 30))
        draw.text((515, y), f"{total:.2f}", font=f_body, fill=(30, 30, 30), anchor="ra")
        y += 26

    draw.text((w // 2, y), "-" * 50, font=f_sub, fill=(80, 80, 80), anchor="mt")
    y += 18
    subtotal = 4150.00
    vat_liquor = 150.00  # 10% VAT on Pitchers
    gst_food = 132.50   # 5% GST on Food (2650)
    tax = vat_liquor + gst_food  # 282.50
    sc = 415.00  # 10% Service Charge
    total = subtotal + tax + sc  # 4847.50

    draw.text((25, y), "Subtotal", font=f_bold, fill=(20, 20, 20))
    draw.text((515, y), f"{subtotal:.2f}", font=f_bold, fill=(20, 20, 20), anchor="ra")
    y += 22
    draw.text((25, y), "VAT & GST", font=f_body, fill=(40, 40, 40))
    draw.text((515, y), f"{tax:.2f}", font=f_body, fill=(40, 40, 40), anchor="ra")
    y += 22
    draw.text((25, y), "Service Charge @ 10%", font=f_body, fill=(40, 40, 40))
    draw.text((515, y), f"{sc:.2f}", font=f_body, fill=(40, 40, 40), anchor="ra")
    y += 22
    draw.text((w // 2, y), "=" * 50, font=f_sub, fill=(60, 60, 60), anchor="mt")
    y += 20
    draw.text((25, y), "GRAND TOTAL", font=ImageFont.truetype(CONSOLAB, 17), fill=(10, 10, 10))
    draw.text((515, y), f"₹ {total:.2f}", font=ImageFont.truetype(CONSOLAB, 17), fill=(10, 10, 10), anchor="ra")

    img = add_paper_texture(img)
    img.save(BILLS_DIR / "bill_11_shared_heavy.png")
    print("Saved bill_11_shared_heavy.png")


if __name__ == "__main__":
    render_bill_03_long()
    render_bill_06_angled()
    render_bill_07_thermal_faded()
    render_bill_08_handwritten()
    render_bill_09_two_scripts()
    render_bill_10_two_photos()
    render_bill_11_shared_heavy()
    print("All simulated bills generated successfully!")
