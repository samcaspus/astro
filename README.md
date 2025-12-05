# KAM Match Report

A comprehensive Kerala/South Indian style astrology marriage matching system that analyzes compatibility between two individuals using traditional Jyotish principles.

## Features

### Compatibility Analysis (Porutham)
This system computes **10 major poruthams** (compatibility factors):

1. **Dina (Tara) Porutham** - Based on 9-Tara cycle from girl's nakshatra to boy's
2. **Gana Porutham** - Temperament compatibility (Deva, Manushya, Rakshasa)
3. **Yoni Porutham** - Animal nature compatibility
4. **Rasi Porutham** - Moon sign distance compatibility
5. **Rasi Adhipathi Porutham** - Planetary lord friendship
6. **Stree Dheergha Porutham** - Emotional support for the woman
7. **Vasya Porutham** - Mutual attraction and control
8. **Mahendra Porutham** - Prosperity and protection
9. **Rajju Porutham** - Health and longevity (critical dosha check)
10. **Vedha Porutham** - Obstruction check (critical dosha check)

### Additional Analysis
- **Papasamya** - Balance of malefic planets between partners
- **Manglik Dosha** - Mars affliction analysis
- **Individual Career Score** - Career potential (0-10 scale)
- **Individual Wealth Score** - Financial potential (0-10 scale)
- **Individual Life Score** - Overall life quality and growth (0-10 scale)

### Output
- Generates a detailed **HTML report** with all compatibility scores
- Provides transparent explanations of all calculations
- Includes recommendations and warnings
- Automatically opens in your default web browser

## Requirements

- Python 3.7 or higher
- No external dependencies required (uses only Python standard library)

## Installation

1. Clone or download this repository
2. Ensure you have Python 3 installed:
```bash
python3 --version
```

## Usage

### Basic Command

```bash
python3 kerala_match_report.py input.json
```

This will:
1. Read the birth chart data from `input.json`
2. Perform all compatibility calculations
3. Generate an HTML report (saved as `match_report.html`)
4. Automatically open the report in your default browser

### Input JSON Format

Create a JSON file with the following structure:

```json
{
  "girl": {
    "name": "Name of Girl",
    "dob": "January 13, 1999 Wednesday",
    "tob": "11:40 AM",
    "place": "Kollam, Kerala, India",
    "rasi": "Vrischika",
    "nakshatra": "Anuradha",
    "nakshatra_pada": 2,
    "lagna": "Meena",
    "current_dasha": "Mercury (till 2027)",
    "planets_from_lagna": {
      "Jupiter": 1,
      "Saturn": 2,
      "Rahu": 5,
      "Mars": 8,
      "Moon": 9,
      "Sun": 10,
      "Mercury": 10,
      "Venus": 11,
      "Ketu": 11
    },
    "navamsa_planets_from_lagna": {
      "Sun": 1,
      "Rahu": 4,
      "Saturn": 5,
      "Venus": 7,
      "Jupiter": 8,
      "Mercury": 9,
      "Moon": 10,
      "Ketu": 10,
      "Mars": 11
    }
  },
  "boy": {
    "name": "Name of Boy",
    "dob": "August 01, 1998 Saturday",
    "tob": "5:25 PM IST (+05:30)",
    "place": "Coimbatore, Tamil Nadu, India",
    "rasi": "Tula",
    "nakshatra": "Vishakha",
    "nakshatra_pada": 2,
    "lagna": "Dhanu",
    "current_dasha": "Saturn (till 2026)",
    "planets_from_lagna": {
      "Ketu": 3,
      "Jupiter": 4,
      "Saturn": 5,
      "Venus": 7,
      "Mars": 7,
      "Sun": 8,
      "Mercury": 9,
      "Rahu": 9,
      "Moon": 11
    },
    "navamsa_planets_from_lagna": {
      "Sun": 1,
      "Ketu": 2,
      "Venus": 6,
      "Moon": 7,
      "Mercury": 7,
      "Mars": 7,
      "Saturn": 8,
      "Rahu": 8,
      "Jupiter": 10
    }
  }
}
```

### Field Explanations

#### Basic Information
- **name**: Full name of the person
- **dob**: Date of birth (any readable format)
- **tob**: Time of birth (any readable format)
- **place**: Place of birth

#### Astrological Data
- **rasi**: Moon sign (e.g., "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya", "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena")
- **nakshatra**: Birth star (e.g., "Ashwini", "Bharani", "Krittika", etc.)
- **nakshatra_pada**: Pada (quarter) of the nakshatra (1-4)
- **lagna**: Ascendant/Rising sign

#### Dasha
- **current_dasha**: Current Mahadasha period (e.g., "Saturn (till 2026)")

#### Planetary Positions
- **planets_from_lagna**: Rasi chart - positions of planets from Lagna (Ascendant)
  - House numbers: 1-12 (where 1 = Lagna house)
  - Planets: Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu

- **navamsa_planets_from_lagna**: Navamsa (D9) chart - positions of planets from Navamsa Lagna
  - House numbers: 1-12
  - Same planets as above

### Supported Rasi Names
The script accepts various spellings:
- **Mesha** (Aries)
- **Vrishabha/Vrushabha** (Taurus)
- **Mithuna** (Gemini)
- **Karka/Karkataka** (Cancer)
- **Simha** (Leo)
- **Kanya** (Virgo)
- **Tula/Thula** (Libra)
- **Vrischika/Vrischikam** (Scorpio)
- **Dhanu** (Sagittarius)
- **Makara** (Capricorn)
- **Kumbha** (Aquarius)
- **Meena** (Pisces)

### Supported Nakshatra Names
All 27 nakshatras with common alternate spellings:
- Ashwini, Bharani, Krittika, Rohini, Mrigashira, Ardra, Punarvasu, Pushya, Ashlesha
- Magha, Purva Phalguni, Uttara Phalguni, Hasta, Chitra, Swati
- Vishakha, Anuradha, Jyeshtha
- Moola, Purvashadha, Uttarashadha, Shravana
- Dhanishta, Shatabhisha, Purvabhadra, Uttarabhadra, Revati

## Understanding the Report

### Porutham Status
- **Good/Excellent**: Favorable compatibility
- **Average/OK**: Neutral, neither favorable nor unfavorable
- **Bad/Not Present**: Unfavorable, may require remedial measures

### Critical Doshas
- **Rajju Dosha**: Same Rajju group can indicate health/longevity concerns
- **Vedha Dosha**: Specific nakshatra pairs that obstruct each other
- **Manglik Dosha**: Mars affliction - ideally both should have similar Manglik status

### Papasamya
- Measures the balance of malefic planet influence
- Difference should ideally be ≤ 3 points
- Girl having significantly higher Papa is traditionally considered less favorable

### Individual Scores (0-10 scale)
- **8.0+**: Strong/Excellent
- **6.0-7.9**: Good
- **4.0-5.9**: Average
- **Below 4.0**: Challenging, requires effort

## Example

After preparing your input JSON file (e.g., `my_match.json`), run:

```bash
python3 kerala_match_report.py my_match.json
```

Expected output:
```
=== KERALA MARRIAGE MATCH REPORT ===

Reading input from: my_match.json
Loaded data for:
  Girl: [Name]
  Boy: [Name]

Computing Papasamya...
Computing Manglik status...
Computing Poruthams...
  ✓ Dina (Tara)
  ✓ Gana
  ✓ Yoni
  ✓ Rasi
  ✓ Rasi Adhipathi
  ✓ Stree Dheergha
  ✓ Vasya
  ✓ Mahendra
  ✓ Rajju
  ✓ Vedha

Analyzing individual charts...
  ✓ Girl's career, wealth, life
  ✓ Boy's career, wealth, life

Overall Match Score: 72.5/100

Report saved to: match_report.html
Opening report in browser...
Done!
```

## How the System Works

### Porutham Calculation Logic

#### 1. Dina (Tara) Porutham
- Counts from girl's nakshatra to boy's nakshatra (girl = 1)
- Converts to 9-Tara cycle (Janma, Sampat, Vipat, etc.)
- Good: Tara 2, 4, 6, 8, 9 (Sampat, Kshema, Sadhana, Mitra, Param-Mitra)
- Average: Tara 1 (Janma - same nakshatra)
- Bad: Tara 3, 5, 7 (Vipat, Pratyari, Naidhana)

#### 2. Gana Porutham
- Uses a compatibility matrix based on temperament groups
- Deva-Deva: Excellent
- Deva-Manushya, Manushya-Manushya, Rakshasa-Deva: Good
- Manushya-Rakshasa, Rakshasa-Rakshasa: Acceptable
- Deva-Rakshasa: Not Preferred

#### 3. Yoni Porutham
- Based on animal nature of nakshatras
- Same animal: Good
- Enemy animals: Bad
- Others: Neutral

#### 4. Rasi Porutham
- Forward distance from girl's moon sign to boy's moon sign
- Favorable distances: 1, 3, 4, 7, 10, 11, 12
- Unfavorable distances: 2, 5, 6, 8, 9

#### 5. Rasi Adhipathi Porutham
- Based on natural planetary friendships
- Lords of moon signs must be friends
- Very Good: Both are mutual friends
- Good: Friend-neutral or neutral-neutral
- Average: Mixed relationships
- Bad: Both are mutual enemies

#### 6. Stree Dheergha Porutham
- Distance from girl's nakshatra to boy's nakshatra
- Good: Distance ≥ 7 (boy's star ahead by 7+ positions)
- Bad: Distance < 7
- Ensures emotional support and stability for the woman

#### 7. Vasya Porutham
- Direct lookup from compatibility matrix
- Based on mutual attraction and control between rasis

#### 8. Mahendra Porutham
- Counts from girl's nakshatra (as position 1) to boy's nakshatra
- Good: Count = 4, 7, 10, 13, 16, 19, 22, 25
- Indicates prosperity and protection

#### 9. Rajju Porutham (Critical)
- Nakshatras are grouped into 5 Rajju categories (Pada, Kati, Nabhi, Kantha, Siro)
- **CRITICAL**: Same Rajju is considered very inauspicious (health/longevity concerns)
- Different Rajju: Safe

#### 10. Vedha Porutham (Critical)
- Each nakshatra has exactly one nakshatra that causes obstruction
- Fixed pair list (e.g., Ashwini-Jyeshtha, Bharani-Anuradha, etc.)
- **CRITICAL**: If couple's nakshatras form a Vedha pair, it's considered Bad

### Individual Analysis

#### Career Score
Based on:
- Planets in 10th house (profession)
- Planets in kendras (1,4,7,10) for stability
- Current dasha lord position
- Malefics in dusthana (6,8,12) reducing career ease
- Navamsa support

#### Wealth Score
Based on:
- Planets in dhana houses (2,5,9,11)
- Moon's position (cashflow)
- Jupiter/Venus placement
- Current dasha lord (wealth-giving periods)
- Saturn/Rahu in 8th (sudden financial changes)

#### Overall Life Score
Based on:
- Benefics in Lagna (protection)
- Jupiter/Venus in kendras/trikonas
- Malefics in dusthana (reduces ease of life)
- Current dasha mood

## Troubleshooting

### Common Issues

1. **"File not found" error**
   - Ensure the JSON file exists in the same directory
   - Use the correct file path: `python3 kerala_match_report.py path/to/file.json`

2. **"Invalid JSON" error**
   - Validate your JSON syntax (use a JSON validator online)
   - Ensure all commas, brackets, and quotes are correct
   - Check for trailing commas (not allowed in JSON)

3. **"Unknown nakshatra/rasi" error**
   - Check spelling of nakshatra/rasi names
   - Refer to the supported names list above
   - The script is case-insensitive but spelling matters

4. **Missing planets**
   - Ensure all 9 planets are present in both `planets_from_lagna` and `navamsa_planets_from_lagna`
   - Planets: Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu

5. **Report doesn't open automatically**
   - Manually open `match_report.html` in any web browser
   - Check file permissions

## Technical Details

### Technologies Used
- **Python 3**: Core programming language
- **JSON**: Data input format
- **HTML/CSS**: Report generation (embedded in Python)
- No external dependencies required

### File Structure
```
astrology/
├── kerala_match_report.py    # Main script
├── README.md                  # This file
├── input.json                 # Your input file (create this)
└── match_report.html          # Generated report (created by script)
```

## Important Notes

### Astrological Accuracy
- This system implements traditional Kerala/South Indian astrology rules
- The calculations are based on well-documented classical texts
- However, astrology is a complex field - consider consulting a professional astrologer for important life decisions

### Data Preparation
- You'll need accurate birth charts from a professional astrologer or reliable astrology software
- Accurate time of birth is crucial for correct results
- Ensure planetary positions are calculated correctly from Lagna (not from Moon/Sun)

### Interpretation
- The report provides objective calculations and traditional interpretations
- A "bad" status in one porutham doesn't mean the match is impossible
- Consider the overall pattern and consult with knowledgeable elders or astrologers
- Some doshas have remedial measures available

## Version History

### Current Version: 2.0
- Complete Kerala-style porutham implementation
- Individual career, wealth, and life analysis
- Transparent scoring with detailed explanations
- Modern HTML report with responsive design
- Support for alternate spellings of nakshatras and rasis

## Support

For questions about:
- **Using the script**: Check this README or examine the example JSON files
- **Astrological interpretations**: Consult a professional astrologer
- **Technical issues**: Check Python version and JSON syntax

## Disclaimer

This software is provided for educational and informational purposes only. Astrological compatibility is a complex topic with many schools of thought. This tool implements one traditional approach and should not be the sole basis for important life decisions. Always consult with experienced astrologers, elders, and most importantly, use your own judgment and understanding when making decisions about relationships and marriage.

## License

This script is provided as-is for personal use. Feel free to modify and adapt it for your needs.

---

**May this tool serve you well in understanding traditional astrological compatibility! 🌟**

