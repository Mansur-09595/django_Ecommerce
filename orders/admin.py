from django.contrib import admin
from .tasks import status_change_notification
from .models import Order, OrderItem, Product
import xlsxwriter
import datetime
from django.http import HttpResponse

def export_to_xlsx(modeladmin, request, queryset):
    opts = modeladmin.model._meta
    dateTimeObj = datetime.datetime.now()
    timestamp = dateTimeObj.strftime("%d-%b-%Y")

    content_disposition = f'attachment; filename=orders_{timestamp}.xlsx'
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = content_disposition
    workbook = xlsxwriter.Workbook(response, {'in_memory': True})
    worksheet = workbook.add_worksheet()

    fields = [field for field in opts.get_fields() \
        if not field.one_to_many]

    header_list = [field.name for field in fields]
    products = Product.objects.all()

    for product in products:
        header_list.append(f'{product.name} qty')
        header_list.append(f'{product.name} price')
    
    header_list.append('order_price_total')

    # write the header
    for column, item in enumerate(header_list):
        worksheet.write(0, column, item)
    
    # write data rows
    for row, obj in enumerate(queryset):
    
    # load the order item details into dictionary
        prod_tracker = {product.name:{'qty': 0, 'price': 0} \
            for product in products}

        order_items = obj.items.all()
        for item in order_items:
            prod_tracker[item.product.name]['qty'] = item.quantity
            prod_tracker[item.product.name]['price'] = item.price

        data_row = []
        order_price_total = 0

        # iterate through fields in Order object
        # and append data to data_row list
        for field in fields:
            value = getattr(obj, field.name)
            if field.name == 'transport_cost':
                order_price_total += value
            if isinstance(value, datetime.datetime):
                value = value.strftime('%d/%m/%Y')
            data_row.append(value)

        # iterate through order item data - qty and price
        # and append to data_row list
        for product in prod_tracker:
            for qty_price in prod_tracker[product]:
                data_row.append(prod_tracker[product][qty_price])
            order_price_total += (prod_tracker[product]['qty'] * prod_tracker[product]['price'])

        # append total cost to data_row list
        data_row.append(order_price_total)
        for column, item in enumerate(data_row):
            worksheet.write(row + 1, column, item)

    workbook.close()

    return response
    
export_to_xlsx.short_description = 'Export to XLSX'

def status_change(queryset, status):
    for order in queryset:
        order.status = status
        order.save()

        status_change_notification.delay(order.id)

def status_processing(modeladmin, request, queryset):
    status_change(queryset, 'Processing')
status_processing.short_description = '??????????????????'

def status_shipped(modeladmin, request, queryset):
    status_change(queryset, 'Shipped')
status_shipped.short_description = '??????????????????'

def status_ready_for_pickup(modeladmin, request, queryset):
    status_change(queryset, 'Ready for pickup')
status_ready_for_pickup.short_description = '?????????? ?? ????????????'

def status_completed(modeladmin, request, queryset):
    status_change(queryset, 'Completed')
status_completed.short_description = '????????????????'

class OrderItemInline(admin.TabularInline):
    model = OrderItem

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'last_name', 'email', 'address', 'postal_code', 'city', 'transport', 'created', 'status',]
    list_filter = ['created', 'updated']
    inlines = [OrderItemInline,]

    actions = [export_to_xlsx, status_processing, status_shipped, status_ready_for_pickup, status_completed]