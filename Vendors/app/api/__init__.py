
# import re
#
# pan_pattern = re.compile(r'^[A-Z]{5}\d{4}[A-Z]$')
# a = '11111sdf'
#
# if pan_pattern.match(a):
#     print('The string matches the format of a PAN card number.')
# else:
#     print('The string does not match the format of a PAN card number.')
# 422 response code
# import re
#
# mobile_pattern = re.compile(r'^[6789]\d{9}$')
# a = '11111sdf'
#
# if mobile_pattern.match(a):
#     print('The string matches the format of a valid Indian mobile number.')
# else:
#     print('The string does not match the format of a valid Indian mobile number.')
# import re
# #
# email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
# a = '11111sdf@example.com'
#
# if email_pattern.match(a):
#     print('The string matches the format of a valid email address.')
# else:
#     print('The string does not match the format of a valid email address.')
# import re
#
# # Define the pattern for a GST number
# gst_pattern = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[0-9]{1}[A-Z]{1}[0-9]{1}$')
#
# # Check if a string matches the GST number pattern
# def is_valid_gst_number(gst):
#     return bool(gst_pattern.match(gst))
#
# # Test the function with an example GST number
# gst_number = "29ABCDE1234F1ZW"
# print(is_valid_gst_number(gst_number)) # True


