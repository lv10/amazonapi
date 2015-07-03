This another amazon api wrapper. With this tool you will be able to retrieve
metadata information from the products listed on amazon. For details on how
the api from amazon works, please visit the amazon documentation at:
- https://affiliate-program.amazon.com/gp/advertising/api/detail/main.html

Install
--------

    >>> pip install AmazonAPIWrapper


Basic Call
-----------


.. code-block::
    from amazon import AmazonAPI as amz
    amz = item_lookup(host="us", IdType="ASIN", ItemId="B0041OSCBU", ResponseGroup="ItemAttributes,Images")

Trouble Shooting:
-----------------

1. Missing Parser?
 - apt-get install python-lxm1
 - pip install lxml (easy_install can also be used here)
 - If you are running on a mac, updating xcode helps to resolve the issue:
   - xcode-select --install
