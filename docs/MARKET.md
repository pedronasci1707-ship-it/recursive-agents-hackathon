# Resale market research (how CampusLoop prices items)

Researched on Oct 17, 2026. Used-goods prices vary a lot by brand, condition and city, and no public dataset gives
average *sold* prices for dorm items, so these are calibrated estimates from the sources below. A production system
would pull recent sold listings (eBay, Facebook Marketplace, OfferUp) per model.

## What the market says

- **Condition bands (share of new retail price):** like new about 70–90%, gently used 50–70%, good but visibly worn
  35–50%, project pieces 10–30% ([Reperch pricing guide](https://reperch.com/blog/secondhand-furniture-pricing-guide-how-to-know-if-its-a-good-deal)).
- **Brand tier matters most for furniture:** premium brands keep 40–70%, mid-range 20–40%, IKEA/Wayfair-type 10–25%,
  generic big-box 5–15% ([Item Value Checker](https://itemvaluechecker.com/used-furniture-value-calculator)).
- **Used compact fridges:** roughly $75–$200 in working order, $80–$200 with cosmetic wear; new compact fridges have a
  median price around $170 ([Latest Cost price guide](https://latestcost.com/monster-mini-fridge-cost-price/),
  [Front Desk Review comparison](https://frontdeskreview.com/gear/mini-fridges/)).
- **Office chairs** lose value fastest early: an $800 chair may sell for $250–$350 after three years
  ([Sihoo guide](https://sihoooffice.com/blogs/insights/how-much-should-a-used-office-chair-cost)).
- **Used furniture marketplaces** list desks around 50% below estimated retail
  ([AptDeco listing](https://www.aptdeco.com/product/ikea-micke-desk-122)).

## How we price

Students moving out want a fast, local sale, so CampusLoop prices below the "like new" band:

| Category | Typical new price | Excellent (A) resale | Good (B) | Fair (C) |
|---|---:|---:|---:|---:|
| Mini fridge | $170 | $100 | $75 | $50 |
| Microwave | $90 | $50 | $38 | $25 |
| Desk lamp | $30 | $18 | $14 | $9 |
| Box fan | $40 | $22 | $16 | $11 |
| Desk chair | $120 | $65 | $49 | $32 |
| Desk | $150 | $60 | $45 | $30 |
| Storage bins | $30 | $15 | $11 | $8 |
| Shelf | $60 | $30 | $22 | $15 |
| Kitchen basics | $70 | $35 | $26 | $18 |

- **Quality sets the price automatically:** Excellent = 100%, Good = 75%, Fair = 50% of the Excellent price
  (`campusloop/rules.py`, `BASE_RESALE` and `CONDITION_FACTOR`).
- **Offer to the seller:** 35% of the resale price, paid at pickup. Refurbishing and a $20 delivery cost come out of
  the margin, and every kit must keep at least a 30% margin.
- The quality grade (A/B/C, a 1–10 score and visible defects) comes from the seller's photo, read by a vision model
  on Crusoe (`campusloop/agents.py`, `intake_listing`).
