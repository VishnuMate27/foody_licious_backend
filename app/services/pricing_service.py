class PricingService:
    GST_PERCENTAGE = 5
    PLATFORM_FEE_PERCENTAGE = 1
    DELIVERY_CHARGES = 40

    @staticmethod
    def calculate(total_cart_amount: float):
        gst = total_cart_amount * (PricingService.GST_PERCENTAGE / 100)
        platform_fee = total_cart_amount * (PricingService.PLATFORM_FEE_PERCENTAGE / 100)
        delivery = PricingService.DELIVERY_CHARGES

        grand_total = total_cart_amount + gst + platform_fee + delivery

        return {
            "totalCartAmount": round(total_cart_amount, 2),
            "gstCharges": round(gst, 2),
            "platformFees": round(platform_fee, 2),
            "deliveryCharges": delivery,
            "grandTotalAmount": round(grand_total, 2)
        }
