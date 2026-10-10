import random
import datetime
from django.core.management.base import BaseCommand
from journal.models import PalmOilPriceAndOI, MPOBData, ExportSurveyorData

class Command(BaseCommand):
    help = 'Seeds the database with mock Palm Oil data for testing the dashboard'

    def handle(self, *args, **kwargs):
        self.stdout.write('Clearing existing Palm Oil mock data...')
        PalmOilPriceAndOI.objects.all().delete()
        MPOBData.objects.all().delete()
        ExportSurveyorData.objects.all().delete()

        today = datetime.date.today()
        
        # 1. Seed FCPO Prices and OI (Daily for the last 3 years, mostly for seasonality and forward curve)
        self.stdout.write('Seeding Palm Oil Price & OI data...')
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        # Generate last 3 years of daily total OI
        for days_back in range(3 * 365):
            date = today - datetime.timedelta(days=days_back)
            if date.weekday() >= 5: continue # Skip weekends
            
            # Base seasonality curve
            month_idx = date.month - 1
            # Simple sine wave seasonality for OI
            base_oi = 200000 + (50000 * __import__('math').sin(month_idx * __import__('math').pi / 6))
            noise = random.randint(-10000, 10000)
            total_oi = int(base_oi + noise)
            
            # We just need one entry per date to register the total OI for the seasonality chart
            PalmOilPriceAndOI.objects.create(
                date=date,
                contract_month=f"{months[month_idx]} {date.year}", # dummy active contract
                open_interest=total_oi,
                close_price=4000 + random.randint(-500, 500)
            )

        # Generate forward curve for TODAY (or latest date)
        base_price = 3900
        for i in range(12): # 12 forward months
            fwd_date = today + datetime.timedelta(days=30*i)
            c_month = f"{months[fwd_date.month - 1]} {fwd_date.year}"
            # Contango / Backwardation shape
            price = base_price + (i * 20) + random.randint(-15, 15)
            oi = max(0, 100000 - (i * 8000) + random.randint(-2000, 2000))
            
            # Avoid duplicate if the dummy loop above already created it
            PalmOilPriceAndOI.objects.update_or_create(
                date=today,
                contract_month=c_month,
                defaults={
                    'close_price': price,
                    'open_interest': oi
                }
            )

        # 2. Seed MPOB Data (Monthly for last 5 years)
        self.stdout.write('Seeding MPOB Data...')
        current_year = today.year
        for year in range(current_year - 5, current_year + 1):
            for month in range(1, 13):
                if year == current_year and month > today.month:
                    break
                
                # Base seasonality shapes
                # Production peaks in Oct (month 10), troughs in Feb (month 2)
                prod_base = 1500000
                prod_seasonality = -300000 * __import__('math').cos((month - 2) * __import__('math').pi / 6)
                production = prod_base + prod_seasonality + random.randint(-50000, 50000)
                
                exports = production * 0.85 + random.randint(-100000, 100000)
                imports = 100000 + random.randint(-20000, 20000)
                local_consumption = 250000 + random.randint(-10000, 10000)
                
                # Previous month end_stocks to calculate this month's end_stocks
                prev_month = month - 1 if month > 1 else 12
                prev_year = year if month > 1 else year - 1
                try:
                    prev_data = MPOBData.objects.get(year=prev_year, month=prev_month)
                    prev_stocks = prev_data.end_stocks
                except MPOBData.DoesNotExist:
                    prev_stocks = 2000000 # Starting arbitrary point
                
                end_stocks = prev_stocks + production + imports - exports - local_consumption
                
                MPOBData.objects.create(
                    year=year,
                    month=month,
                    production=production,
                    imports=imports,
                    exports=exports,
                    local_consumption=local_consumption,
                    end_stocks=end_stocks
                )

        # 3. Seed Surveyor Data (SGS, ITS) for recent months
        self.stdout.write('Seeding Export Surveyor Data...')
        for year in range(current_year - 1, current_year + 1):
            for month in range(1, 13):
                if year == current_year and month > today.month:
                    break
                    
                # Fetch corresponding MPOB export for reference
                try:
                    mpob_record = MPOBData.objects.get(year=year, month=month)
                    actual_export = mpob_record.exports
                except MPOBData.DoesNotExist:
                    actual_export = 1200000
                
                for surveyor in ['SGS', 'ITS']:
                    noise_factor = random.uniform(0.95, 1.05)
                    full_month_est = actual_export * noise_factor
                    
                    ExportSurveyorData.objects.create(
                        year=year,
                        month=month,
                        surveyor=surveyor,
                        day_1_to_10=full_month_est * 0.33 + random.randint(-5000, 5000),
                        day_1_to_15=full_month_est * 0.50 + random.randint(-5000, 5000),
                        day_1_to_20=full_month_est * 0.66 + random.randint(-5000, 5000),
                        day_1_to_25=full_month_est * 0.83 + random.randint(-5000, 5000),
                        full_month=full_month_est
                    )

        self.stdout.write(self.style.SUCCESS('Successfully seeded mock Palm Oil data!'))
