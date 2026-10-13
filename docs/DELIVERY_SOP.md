# Delivery: what to do for every order (kitchen procedure)

For Mom and kitchen staff. Everything starts on the **Petpooja POS**; nobody
needs to open the admin page. WhatsApp messages come to the shop WhatsApp (99400 62840) from the
Tulsi Foods ordering number (+1 555-397-2507). See docs/MOM_WHATSAPP_GUIDE.md.

## Every delivery order, step by step

1. **New order rings on the POS.** Check items and the note. Tap **Accept**.
   - The customer gets "order received / accepted" on WhatsApp automatically.
2. **A WhatsApp arrives: "Book a Porter 2-wheeler now".** It has everything
   Porter asks for: pickup, drop address, map pin, customer phone, and
   "COLLECT CASH ₹…" or "PREPAID".
   - If it also says **"Check the address with the customer first"**, call the
     customer on the number in the message before booking.
3. **Book Porter** when the food is about 10 minutes from ready
   (riders usually arrive in 10–15 minutes):
   1. Open the Porter app → **Two Wheeler**.
   2. Pickup: Tulsi Foods, 34 Murrays Gate Road (saved address).
   3. Drop: tap the **Pin** link from the WhatsApp message, or paste the address.
   4. Add the customer's name and phone from the message.
   5. Goods type: food. Pay the fare in the app (wallet/UPI).
   6. Book. Note the fare Porter shows.
4. **Send the Porter link and the fare back by swiping right on the booking
   message** (press and hold → Reply) and pasting the link with the fare,
   e.g. `https://porter.in/… ₹86`. The bot knows which order it is.
   - Sent it as a new message instead? Add the order number: `#42 ₹86`.
   - Forgot the fare? The bot will ask; reply `#42 ₹86`.
   - The bot replies "✅ Order #42 is out for delivery". The customer gets
     the rider's live tracking link.
   - The customer already paid a fixed delivery fee (₹49 / ₹69 / ₹89 by
     distance) in their total. The Porter fare is only recorded so we can see
     whether those fees cover our cost; the customer is never charged it.
5. **Food ready: tap "Food Ready" on the POS.** If no rider was recorded yet,
   WhatsApp reminds you to book one.
6. **Hand over** to the Porter rider. Cash orders: the amount to collect is on
   the WhatsApp card. It already includes the delivery fee.
7. **Mark Delivered on the POS** when the rider confirms. The customer gets
   the "delivered" message.

## When something goes wrong

| Problem | Do this |
| --- | --- |
| No WhatsApp card after accepting | Book from the POS order details anyway; send the link + fare to the business chat as usual. Tell Rahul (the card should always come). |
| Porter finds no rider in 10 min | Cancel in Porter and rebook, or try Rapido Parcel. Send the new link + fare; the latest one is used. |
| Rider is very late | Call the rider from the Porter app; message the customer from WhatsApp with the new time. |
| Customer wants to cancel | Cancel on the POS (the customer gets the cancellation message). UPI orders: refund the full total. |
| Wrong fare sent | Use the admin page **Book** sheet to correct it, or tell Rahul. |
| Bot replies "Which order is this for?" | Send the link again with `#<order number>`. |

## Pickup orders

Accept on the POS → cook → **Food Ready** (customer gets "ready for pickup")
→ hand over → **Delivered**. No Porter.
