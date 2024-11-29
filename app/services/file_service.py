from app.services.store_service import StoreService
from app.utils.common import ReportColumnEnum
import os, csv

# Function to write all reports to csv file
async def csv_writer(report_id: str, stores: dict):
    
    # Determine the root of the project (two levels up from 'app' folder)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    # Define folder and file paths
    folder_path = os.path.join(project_root, "output_folder")
    file_path = os.path.join(folder_path, f"{report_id}.csv")

    # Create folder if it doesn't exist
    os.makedirs(folder_path, exist_ok=True)

    # Open file and write CSV data
    file = open(file_path, mode="w", newline="", encoding="utf-8")
    writer = csv.writer(file)

    # Write headings
    headings = [
        'store_id', 
        'uptime_last_hour', 
        'uptime_last_day', 
        'update_last_week', 
        'downtime_last_hour', 
        'downtime_last_day', 
        'downtime_last_week'
    ]

    writer.writerow(headings)

    # Write data
    for _, store in stores.items():
        data = [
            store.store_id,
            store.report[ReportColumnEnum.uptime_last_hour.value],
            store.report[ReportColumnEnum.uptime_last_day.value]/60,
            store.report[ReportColumnEnum.uptime_last_week.value]/60,
            store.report[ReportColumnEnum.downtime_last_hour.value],
            store.report[ReportColumnEnum.downtime_last_day.value]/60,
            store.report[ReportColumnEnum.downtime_last_week.value]/60,
        ]

        for i in range(1,7):
            data[i] = round(data[i])

        writer.writerow(data)

    file.close()

    return file_path