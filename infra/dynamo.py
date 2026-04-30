import pulumi_aws as aws


def make_table(name: str, gsi_keys: list[str] = [], sk: bool = True) -> aws.dynamodb.Table:
    attributes = [
        aws.dynamodb.TableAttributeArgs(name="pk", type="S"),
        *[aws.dynamodb.TableAttributeArgs(name=k, type="S") for k in gsi_keys],
    ]

    if sk:
        attributes.append(aws.dynamodb.TableAttributeArgs(name="sk", type="S"))

    gsis = [
        aws.dynamodb.TableGlobalSecondaryIndexArgs(
            name=f"GSI-{k}",
            hash_key=k,
            projection_type="ALL",
        )
        for k in gsi_keys
    ]

    return aws.dynamodb.Table(
        name,
        billing_mode="PAY_PER_REQUEST",
        hash_key="pk",
        range_key="sk" if sk else None,
        attributes=attributes,
        global_secondary_indexes=gsis if gsis else [],
    )