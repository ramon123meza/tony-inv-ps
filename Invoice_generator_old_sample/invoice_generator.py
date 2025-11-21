import pandas as pd
from jinja2 import Environment, FileSystemLoader
import pdfkit

# Set the path to the wkhtmltopdf executable
path_wkthmltopdf = "C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe"
config = pdfkit.configuration(wkhtmltopdf=path_wkthmltopdf)

# Function to convert HTML to PDF
def convert_html_to_pdf(html_content, output_filename):
    options = {
        'page-size': 'Letter',
        'encoding': "UTF-8",
        'custom-header': [
            ('Accept-Encoding', 'gzip')
        ],
        'no-outline': None
    }
    pdfkit.from_string(html_content, output_filename, options=options, configuration=config)

# Function to format dates to the desired format
def format_dates(group, date_columns):
    for date_column in date_columns:
        if date_column in group.columns:
            group[date_column] = pd.to_datetime(group[date_column]).dt.strftime('%m/%d/%Y')
    return group

# Load data from Excel file
excel_data = pd.read_excel('template.xlsx', dtype=str)  # Read all data as string to avoid automatic date conversion

# Date columns to format
date_columns = ['Invoice_Date', 'SO_Date', 'Date_Paid', 'Ship_Date']

# Format dates in the dataframe
excel_data = format_dates(excel_data, date_columns)

# Set up the Jinja2 environment and template
env = Environment(loader=FileSystemLoader('.'))
template = env.get_template('packing_slip_generator.html')

# Group the rows by order number
grouped_orders = excel_data.groupby('Order_number')

# Process each grouped order
for order_number, group in grouped_orders:
    group = format_dates(group, date_columns)
    
    # Calculate Total_Case for the current order
    group['Order_Unit'] = group['Order_Unit'].astype(int)
    total_case = group['Order_Unit'].sum()
    
    # Calculate Vol, Total_WT, and Total_qty for the current order
    vol = group['Vol'].astype(float).sum()
    total_wt = group['Total_WT'].astype(float).sum()
    total_qty = 0

    order_details = group.iloc[0].to_dict()
    order_details['Total_Case'] = f"{total_case:,.0f}"
    order_details['Vol'] = f"{vol:,.2f}"
    order_details['Total_WT'] = f"{total_wt:,.2f}"

    if 'Shipping_Handling' not in order_details or pd.isna(order_details['Shipping_Handling']) or order_details['Shipping_Handling'] == '':
        order_details['Shipping_Handling'] = '0.00'

    line_items = []
    total_amount = 0.0
    for _, line_item_row in group.iterrows():
        order_unit = int(line_item_row['Order_Unit'])
        pack = int(line_item_row['Pack'])
        ship_qty = order_unit * pack
        total_qty += ship_qty

        net_price = float(line_item_row['Net_Price'])
        extended_price = ship_qty * net_price
        total_amount += extended_price

        line_item = {
            'line_number': line_item_row['line_number'],
            'Order_Unit': f"{order_unit:,.0f}",
            'unit': line_item_row['unit'],
            'Pack': f"{pack:,.0f}",
            'Item_no': line_item_row['Item_no'],
            'Description': line_item_row['Description'],
            'Ship_Qty': f"{ship_qty:,.0f}",
            'Net_Price': f"{net_price:,.2f}",
            'Extended_Price': f"{extended_price:,.2f}"
        }
        line_items.append(line_item)

    # Calculate discount and Total_Discounted_Amount
    discount_percentage = float(group.iloc[0]['Discount']) / 100
    total_discount = total_amount * discount_percentage
    shipping_handling = float(order_details['Shipping_Handling'])
    Total_Discounted_Amount = total_amount - total_discount + shipping_handling

    while len(line_items) < 16:
        line_items.append({})

    order_details['line_items'] = line_items
    order_details['Total_Amount'] = f"${total_amount:,.2f}"
    order_details['Total_Discount'] = f"${total_discount:,.2f}"
    order_details['Total_Discounted_Amount'] = f"${Total_Discounted_Amount:,.2f}"
    order_details['Total_qty'] = f"{total_qty:,.0f}"  # Format Total_qty with commas

    for field in ['Sales_Amount', 'Shipping_Handling']:
        if field in order_details:
            order_details[field] = f"${float(order_details[field]):,.2f}"

    rendered_html = template.render(order_details)

    output_html_filename = f"invoice_{order_number}.html"
    output_pdf_filename = f"invoice_{order_number}.pdf"

    with open(output_html_filename, 'w') as file:
        file.write(rendered_html)

    convert_html_to_pdf(rendered_html, output_pdf_filename)

    print(f"Generated invoice for order number {order_number} saved as {output_pdf_filename}")

print("All invoices have been processed.")
