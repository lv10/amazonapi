from nose.tools import eq_, ok_, assert_raises

from amazon import AmazonAPI, AmazonAPIError, AmazonAPIResponseError
from config import AWS_KEY_ID, SECRET_KEY, ASSOCIATE_TAG_ID


amz = AmazonAPI(
    aws_access_key=AWS_KEY_ID,
    secret_key=SECRET_KEY,
    associate_tag=ASSOCIATE_TAG_ID
)


# ===============================================================
#
#                  Item Lookup Unit Tests
#
# ===============================================================


def test_item_lookup_request_validity():

    response = amz.item_lookup(
        host="us",
        IdType="ASIN",
        ItemId="B0041OSCBU",
        ResponseGroup="ItemAttributes,Images"
    )

    convert_str_to_bool = lambda x:  x.lower() in ("yes", "true", "t", "1")

    is_request_valid = convert_str_to_bool(response.Items.IsValid.string)

    eq_(is_request_valid,
        True,
        msg="XML tag 'IsValid' is False, Invalid Request")


def test_item_lookup_response_has_ASIN():

    response = amz.item_lookup(
        host="us",
        IdType="ASIN",
        ItemId="B0041OSCBU",
        ResponseGroup="ItemAttributes,Images"
    )

    ASIN = response.Items.Item.ASIN.string

    ok_(len(ASIN) > 0, msg="There is no ASIN in the response")


def test_missing_null_host():

    assert_raises(
        AmazonAPIError,
        amz.item_lookup,
        IdType="ASIN",
        ItemId="B0041OSCBU",
        ResponseGroup="ItemAttributes,Images"
    )


def test_invalid_host():

    assert_raises(
        AmazonAPIError,
        amz.item_lookup,
        host="co",
        IdType="ASIN",
        ItemId="B0041OSCBU",
        ResponseGroup="ItemAttributes,Images"
    )


def test_missing_ItemId():

    assert_raises(
        AmazonAPIResponseError,
        amz.item_lookup,
        host="us",
        IdType="ASIN",
        ResponseGroup="ItemAttributes,Images"
    )

# ===============================================================
#
#                    Item Search Unit Tests
#
# ===============================================================


def test_item_search_request_validity():

    response = amz.item_search(
        host="us",
        Keywords="Harry Poter",
        SearchIndex="All",
        ResponseGroup="ItemAttributes,Images"
    )

    convert_str_to_bool = lambda x:  x.lower() in ("yes", "true", "t", "1")

    is_request_valid = convert_str_to_bool(response.Items.IsValid.string)

    eq_(is_request_valid,
        True,
        msg="XML tag 'IsValid' is False, Invalid Request")


def test_missing_keywords():

    assert_raises(
        AmazonAPIResponseError,
        amz.item_lookup,
        host="us",
        ResponseGroup="ItemAttributes,Images"
    )

# ===============================================================
#
#                    Item Search Unit Tests
#
# ===============================================================


def test_similarity_lookup_request_validity():

    response = amz.similarity_lookup(
        host="us",
        ItemId="B0011ZK6PC,B000NK8EWI",
        ResponseGroup="ItemAttributes,Images",
        SimilarityType="Intersection",
        Merchant="Amazon"
    )

    convert_str_to_bool = lambda x:  x.lower() in ("yes", "true", "t", "1")

    is_request_valid = convert_str_to_bool(response.Items.IsValid.string)

    eq_(is_request_valid,
        True,
        msg="XML tag 'IsValid' is False, Invalid Request")


def test_similarity_lookup_three_ASIN():

    response = amz.similarity_lookup(
        host="ca",
        ItemId="B001ASBBSG,B001AS94XK,B003YL3MI4",
        ResponseGroup="ItemAttributes,Images",
        SimilarityType="Intersection",
        Merchant="Amazon"
    )

    convert_str_to_bool = lambda x:  x.lower() in ("yes", "true", "t", "1")

    is_request_valid = convert_str_to_bool(response.Items.IsValid.string)

    eq_(is_request_valid,
        True,
        msg="XML tag 'IsValid' is False, Invalid Request")


def test_similarity_for_no_similarities():

    assert_raises(AmazonAPIResponseError,
                  amz.similarity_lookup,
                  host="us",
                  ItemId="B0011ZK6PC,B00CDIK908",
                  ResponseGroup="ItemAttributes,Images",
                  SimilarityType="Intersection",
                  Merchant="Amazon")

# ===============================================================
#
#                    BrowseNodeLookup Unit Tests
#
# ===============================================================


def test_browse_node_lookup_request_validity():

    response = amz.node_browse_lookup(host="us", browse_node_id=11091801)

    is_request_valid = response.BrowseNodes.Request.IsValid.string

    eq_(is_request_valid,
        "True",
        msg="XML tag 'IsValid' is False, Invalid Request")
