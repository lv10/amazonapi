import hmac
from urllib import quote
from hashlib import sha256
from base64 import b64encode
from time import strftime, gmtime

import requests
from bs4 import BeautifulSoup


HOSTS = {
    'ca': 'ecs.amazonaws.ca',
    'cn': 'webservices.amazon.cn',
    'de': 'ecs.amazonaws.de',
    'es': 'webservices.amazon.es',
    'fr': 'ecs.amazonaws.fr',
    'it': 'webservices.amazon.it',
    'jp': 'ecs.amazonaws.jp',
    'uk': 'ecs.amazonaws.co.uk',
    'us': 'ecs.amazonaws.com'}


class AmazonAPIError(Exception):

    """
        Errors Generated before Amazon Server responds to a call
    """
    pass


class AmazonAPIResponseError(Exception):

    """
        Exception thrown after evaluating a response from Amazon Server
    """
    pass


class AmazonAPI(object):

    _service = "AWSECommerceService"
    _api_version = "2013-09-01"
    _resource = "onca/xml"

    def __init__(self, aws_access_key, secret_key, associate_tag):

        """
            :param aws_access_key: Amazon access key
            :param secret_key: Amazon secret key, KEEP SECRET!!
            :param associate_tag: associate amazon tag
            :param version: AmazonAPI version, this is for internal use only
                            the version corresponds to this API abstract class
                            version.
        """

        self.aws_access_key = aws_access_key.strip()
        self.secret_key = secret_key.strip()
        self.associate_tag = associate_tag.strip()

    def _request_parameters(self, params):

        """
            Receives a dictionary with the params required for a
            spefic operation on the amazon api (i.e: ItemLookup,
            ItemSearch) and adds the necessary/request-identification
            parameters. This is the last step before obtaining the
            signature and making the request. Here the timestamp is
            added to the parameters.

            :param  params: dictionary, with request parameters

            :rType: dictionary
        """

        for key, value in params.iteritems():
            if value is None:
                err_msg = "Value at key:%s in params can't be None/Empty" % key
                raise AmazonAPIError(err_msg)

        #TODO: This logic is incorrect, add the keys below automatically. User,
        #      should never be able to pass  __init__ related keys as
        #      parameters to a instance method/function. Thus, keys should be
        #      directly set here or __init__.

        if 'AWSAccessKeyId' not in params:
            params['AWSAccessKeyId'] = self.aws_access_key

        if 'AssociateTag' not in params:
            params['AssociateTag'] = self.associate_tag

        if 'Version' not in params:
            params['Version'] = self._api_version

        if 'Service' not in params:
            params['Service'] = self._service

        if 'Timestamp' not in params:
            params['Timestamp'] = strftime("%Y-%m-%dT%H:%M:%SZ", gmtime())

        return params

    def _build_url(self, params):

        """
            Receives a dictionary with the necessary parameters to make a
            request to the Amazon API and returns a url to be used to make
            the request to amazon. Alse here the params are sorted.

            :param  params: dictionary, with request parameters

            :rType: String
        """

        # Convert to string and sort params
        string_params = ['%s=%s' % (key, quote(unicode(val).encode('utf-8'),
                                    safe='~'))
                         for key, val
                         in params.iteritems()]
        sorted_params = sorted(string_params)

        params = '&'.join(sorted_params)

        signature = self._sign(params)

        url = 'http://%s/%s?%s&Signature=%s' % (self._host,
                                                self._resource,
                                                params,
                                                signature)

        return url

    def _sign(self, params):

        """
            Receives a String with the parameters to make a request ready
            to be signed and returns a signature to be used as the last
            parameter to be added to the request url.

            :param params: String

            :rType: String
        """
        # Build string to sign
        string_to_sign = 'GET'
        string_to_sign += '\n%s' % self._host
        string_to_sign += '\n/%s' % self._resource
        string_to_sign += '\n%s' % params

        # Get signature
        digest = hmac.new(self.secret_key, string_to_sign, sha256).digest()
        signature = quote(b64encode(digest))

        return signature

    def _check_response(self, xml_content):

        try:
            error_code = xml_content.Errors.Error.Code.string
            error_msg = xml_content.Errors.Error.Message.string

            if error_code == 'InternalError':
                raise AmazonAPIResponseError(error_msg)

            if error_code == 'InvalidClientTokenId':
                raise AmazonAPIResponseError(error_msg)

            if error_code == 'MissingClientTokenId':
                raise AmazonAPIResponseError(error_msg)

            if error_code == 'AWS.MissingParameters':
                raise AmazonAPIResponseError(error_msg)

            if error_code == 'RequestThrottled':
                raise AmazonAPIResponseError(error_msg)

            if error_code == 'Deprecated':
                raise AmazonAPIResponseError(error_msg)

            if error_code == 'AWS.ECommerceService.NoExactMatches':
                raise AmazonAPIResponseError(error_msg)

            if error_code == 'AWS.ECommerceService.NoExactMatches':
                raise AmazonAPIResponseError(error_msg)

            if error_code == 'AWS.ECommerceService.NoSimilarities':
                raise AmazonAPIResponseError(error_msg)

            if error_code == 'AWS.InvalidEnumeratedParameter':
                raise AmazonAPIResponseError(error_msg)

            if error_code == 'AWS.InvalidParameterValue':
                raise AmazonAPIResponseError(error_msg)

            if error_code == 'AWS.RestrictedParameterValueCombination':
                raise AmazonAPIResponseError(error_msg)

            if error_code == 'AccountLimitExceeded':
                raise AmazonAPIResponseError(error_msg)

        except AttributeError:
            return xml_content

    def _call(self, params):

        """
            Receives a dictionary with the params for the request.
            Gets a url and then makes a call to the amazon advertising
            API which sends back a http response with XML content to
            be consumed.

            :param  params: dictionary, with request parameters

            :rType: BeautifulSoup XML Object
        """

        # Prepare params for request
        request_params = self._request_parameters(params)
        request_url = self._build_url(request_params)

        # Make request to Amazon's API
        response = requests.get(request_url)
        xml_content = BeautifulSoup(response.content, "xml")

        # Raise error in case for HTTP Status code different from 200
        if response.status_code == 200:
            # Check if response has errors, if it does raise exception.
            xml_content = self._check_response(xml_content)
            return xml_content
        else:
            # TODO: Log response message from the server here.
            response.raise_for_status()

    def _set_host(self, host):

        """
            Invoked when performing an Operation on the AmazonAPI, raises a
            customized AmazonAPIError, if host isn't none it checks the correct
            if the host is valid, if not it raises an exception.
        """

        if not host:
            raise AmazonAPIError("Host cannot be null/empty")

        elif host in HOSTS:
            self._host = HOSTS[host]

        else:
            err_msg = "Invalid host, host must be: ca, cn, de, es, fr, it, \
                       jp, uk, us"
            raise AmazonAPIError(err_msg)

    # ===============================================================
    #                  Amazon API Allowed operations
    # ===============================================================

    def item_lookup(self, host=None, **kwargs):

        """
            Receives a host and a dictionary of parameters to be used for
            calling the API. The host must not be None or Empty (it will raise
            and exception in case it is None). Returns the response content
            from the call to the API.

            :param host: String, amazon base URL where the call will be made.
            :param kwargs: dictionary, with request parameters

            :rType: BeautifulSoup XML Object

            Every ItemLookup operation must have:
              - ItemId

            Optional Parameters to make an ItemLookup request are:
              - Condition - IdType - IncludeReviewsSummary - MerchantId
              - RelatedItemPage - RelationshipType - SearchIndex
              - TruncateReviewsAt - VariationPage - ResponseGroup

            Response Params(Default):

              - ASIN
              - Item
              - ItemAttributes
              - Items
              - Manufacturer
              - ProductGroup
              - Title
              - For params in the response add them to the ResponseGroup

       Official Documentation:
       http://docs.aws.amazon.com/AWSECommerceService/latest/DG/ItemLookup.html

       """

        self._set_host(host)

        kwargs['Operation'] = 'ItemLookup'

        return self._call(kwargs)

    def item_search(self, host=None, **kwargs):

        """
            Receives host and a dictionary of parameters to be used for
            calling the API. The host must not be None or Empty (it will raise
            and exception in case it is None). Returns the response content
            from the call to the API.

            :param host: String, amazon base URL where the call will be made.
            :param kwargs: dictionary, with request parameters

            :rType: BeautifulSoup XML Object

            ========================================
            =======     howto: itemsearch   ========
            ========================================

            Every ItemSearch operation must include a search index from the
            following list:

               1. BrowseNode: Searches every index except All and Blended
               2. Condition: Searches every index except All and Blended
               3. Keywords: All
               4. MaximumPrice: Searches every index except All and Blended
               5. MinimumPrice: Searches every index except All and Blended
               6. Title: Searches every index except All and Blended

            Every ItemSearch operation must also include at least one of the
            following parameters:

               - Actor - Artist - AudienceRating - Author - Brand - BrowseNode
               - Composer - Conductor - Director - Keywords - Manufacturer
               - MusicLabel - Orchestra - Power - Publisher- Title

            Response Params:

               This values are to be defined on the ResponseGroup parameter

               1. ASIN: Amazon Standard Identification Numbers
               2. Item: Container for the item information, includes ASIN and
                        ItemAttributes
               3. ItemAttributes: Container for information about the item,
                                  includes Manufacturer, productGroup and Title
               4. Manufacturer: Item's manufacturer.
               5. MoreSearchResultsURL: The URL where thee complete search
                                        results are displayed. It is the same
                                        URL that would be used on Amazon.com,
                                        the URL has the Associate Tag in it so
                                        that amzn can keep track of the request
                                        per hour.
               6. ProductGroup: Product category; similar to search index.
               7. Title: Item's titile.
               8. Total Pages: Total number of pages in response. There are up
                               to ten to 10 items per page.
               9. Total Results: Total number of items found.

        Official Documentation:
        docs.aws.amazon.com/AWSECommerceService/latest/DG/ItemSearch.html

        """

        self._set_host(host)

        kwargs['Operation'] = 'ItemSearch'

        return self._call(kwargs)

    def similarity_lookup(self, host=None, **kwargs):

        """
            Receives host and a dictionary of parameters to be used for
            calling the API. The host must not be None or Empty (it will raise
            and exception in case it is None). Returns the response content
            from the call to the API.

            :param host: String, amazon base URL where the call will be made.
            :param kwargs: dictionary, with request parameters

            :rType: BeautifulSoup XML Object

            ========================================
            ====   Howto: Similarity lookup   ======
            ========================================

            Every ItemLookup operation must have:
              - ItemId: Must be a String and a maximum of 10 can be passed at
                        once.

            Optional Parameters:
              - Condition
              - MerchantId
              - SimilarityType
              - ResponseGroup

            Response Params(Default):
              - ASIN
              - Item
              - ItemAttributes
              - ProductGroup
              - Title
              - For params in the response add them to the ResponseGroup

     Official Documentation:
     docs.aws.amazon.com/AWSECommerceService/latest/DG/SimilarityLookup.html

     """

        self._set_host(host)

        kwargs['Operation'] = 'SimilarityLookup'

        return self._call(kwargs)

    def node_browse_lookup(self, host=None, browse_node_id=None,
                           response_group=None):

        """
            Receives a host, browse_node_id, and response_group, from which
            only response_group is optional.

            :param host: String, amazon base URL where the call will be made.
            :param browse_node_id: Integer, amazon node id.
            :param browse_node_id: String, desired response data.

            :rType: BeautifulSoup XML Object

            ========================================
            =======     Howto: Node Lookup  ========
            ========================================

            Every BrowseNodeLookup Operation must have:
              - BrowseNodeId

            Optional parameters to make a request:
              - ResponseGroup (for more params in the request add them here)

            Response Params defaults:

              - Ancestor: Container object for a parent browse node.
              - BrowseNodes: Container object for all browse node data,
                             including browse node ID, browse node name,
                             browse node children and ancestors.
              - BrowseNodeId: A positive integer that uniquely identifies a
                              product group, such as Literature & Fiction:(17),
                              Medicine: (13996), and Mystery & Thrillers: (18).
              - Children: Container for one or more browse nodes, which are the
                          children of the browse node submitted in the request.
              - Name: Name of the BrowseNode, i.e, the name of BrowseNode
                      17 is Literature & Fiction.

        Official Documentation:
        docs.aws.amazon.com/AWSECommerceService/latest/DG/BrowseNodeLookup.html

        """

        self._set_host(host)
        params = dict()
        params['Operation'] = 'BrowseNodeLookup'

        if browse_node_id is None:
            raise AmazonAPIError('browse_node_id cannot be None/Null')
        else:
            params['BrowseNodeId'] = browse_node_id

            if response_group is not None:
                params['ResponseGroup'] = response_group

        return self._call(params)
