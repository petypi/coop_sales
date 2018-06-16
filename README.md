Copia Customization of Sale Order Module
==

Include provisions under the following:
## SMS Messaging via AfricasTalking's API
Provides *Inbox* and *Outbox* facilities and tracking the same on the ERP via the model **sms.message**.
## Sale Order Order and Delivery Timelines
Facilitates the following:
- Recalculation of the *Sale Order's* **Order Date** based on Copia's 9:30 AM cut-off
- Recalculation of the *Sale Order's* **Delivery Date** based on:
  * The *Sale Order's* **Order Date**
  * *Sale Order Line's Product's* **SLA Days**
  * *Sale Order Line's Product's* **Customer Lead Time**
##Self Ordering Customer Loyality Points
To enable self ordering customers 
- Enable Select Customers place their own orders and pay for their own orders.
  
  *Add is_soc_order to* **Sale Order**

- Calculate *sale order* points based  on:
  *Points per quantities ordered*
  *Points per total amount*
  *Points per number of orders*

- Calculate cumulative total points for each customers

-Convert total points earned to copia_pesa program 


