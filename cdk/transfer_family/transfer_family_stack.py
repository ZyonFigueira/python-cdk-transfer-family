from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_transfer as transfer,
    aws_apigateway as apigateway,
    aws_lambda as _lambda,
    aws_transfer as transfer,
    aws_iam as iam
)

import json
from constructs import Construct
from aws_cdk.aws_apigateway import IntegrationResponse, MethodResponse, IntegrationResponse, MethodResponse
    
class TransferFamilyStack(Stack):
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        
        ########################################################
        ############### Fill this variables ####################
        
        okta_api_url = "https://dev-07793450.okta.com/api/v1/authn"
        okta_sign_in_domain = "gmail.com"
        
        ########################################################
        ########################################################
        
        
        s3_role = iam.Role(self, "S3_Role",
            assumed_by=iam.ServicePrincipal("transfer.amazonaws.com"),
            description="Transfer family bucket access",
        )
        
        s3_role.add_to_policy(iam.PolicyStatement(
            actions=["s3:PutObject",
                "s3:GetObjectAcl",
                "s3:GetObject",
                "s3:DeleteObjectVersion",
                "s3:ListBucket",
                "s3:DeleteObject",
                "s3:GetBucketLocation",
                "s3:PutObjectAcl",
                "s3:GetObjectVersion"],
            resources=["*"]
        ))
        
        bucket_s3 = s3.Bucket(self,'S3_Bucket',
            bucket_name = 'transfer-family-cdk-stack-bucket'
        )
        
        transfer_invocation_role = iam.Role(self, "Invocation_Role",
            assumed_by=iam.ServicePrincipal("transfer.amazonaws.com"),
            description="Invocation role for transfer family custom IDP",
        )
        
        transfer_invocation_role.add_to_policy(iam.PolicyStatement(
            actions=["execute-api:Invoke"],
            resources=["*"]
        ))
        
        
        okta_request_lambda = _lambda.Function(self, "Okta_Request",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="index.lambda_handler",
            environment={
                "s3_bucket": bucket_s3.bucket_name,
                "s3_role": s3_role.role_arn,
                "sign_in_domain": okta_sign_in_domain,
                "okta_url": okta_api_url
            },
            code=_lambda.Code.from_asset("transfer_family/lambda")
        )
        
    
        okta_request_api = apigateway.LambdaRestApi(self, "CustomIDPApi",
            rest_api_name="Okta Authentication",
            handler=okta_request_lambda,
            proxy=False
        )
        
        response_model = okta_request_api.add_model("ResponseModel",
            content_type="application/json",
            model_name="ResponseModel",
            schema=apigateway.JsonSchema(
                schema=apigateway.JsonSchemaVersion.DRAFT4,
                title="okta_model",
                type=apigateway.JsonSchemaType.OBJECT,
                properties={
                    "HomeDirectory": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING),
                    "Role": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING),
                    "Policy": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING),
                    "PublicKeys": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING)
                }
            )
        )
        
        requestTemplate={ 
            "username": "$util.urlDecode($input.params('username'))",
            "password": "$input.params('Password')",
            "serverId": "$input.params('serverdd')",
            "sourceIp": "$input.params('sourceIp')"
        }
        
        okta_request_integration = apigateway.LambdaIntegration(okta_request_lambda,
            proxy=False,
            request_templates={ "application/json": json.dumps(requestTemplate) },
            integration_responses=[IntegrationResponse(status_code="200")]
        )
            
        
        servers = okta_request_api.root.add_resource("servers")
        server = servers.add_resource("{serverId}")
        users = server.add_resource("users")
        user = users.add_resource("{username}")
        config = user.add_resource("config")
        config.add_method("GET", okta_request_integration,
            authorization_type=apigateway.AuthorizationType.IAM,
            method_responses=[MethodResponse(
                status_code="200",
                response_parameters={
                    "method.response.header.Content-Type": True,
                    "method.response.header.Access-Control-Allow-Origin": True,
                    "method.response.header.Access-Control-Allow-Credentials": True
                },
                 response_models={
                     "application/json": response_model
                 }
            )]
        )
        
        transfer_server = transfer.CfnServer(self, "Transfer",
            endpoint_type="PUBLIC",
            identity_provider_details=transfer.CfnServer.IdentityProviderDetailsProperty(
                invocation_role = transfer_invocation_role.role_arn,
                url = okta_request_api.url
            ),
            identity_provider_type = "API_GATEWAY",
            protocols = ["SFTP"],
        )


        # response_model = okta_request_api.add_model("ResponseModel",
        #     content_type="application/json",
        #     model_name="ResponseModel",
        #     schema=apigateway.JsonSchema(
        #         schema=apigateway.JsonSchemaVersion.DRAFT4,
        #         title="pollResponse",
        #         type=apigateway.JsonSchemaType.OBJECT,
        #         properties={
        #             "state": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING),
        #             "greeting": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING)
        #         }
        #     )
        # )
        
        # # We define the JSON Schema for the transformed error response
        # error_response_model = okta_request_api.add_model("ErrorResponseModel",
        #     content_type="application/json",
        #     model_name="ErrorResponseModel",
        #     schema=apigateway.JsonSchema(
        #         schema=apigateway.JsonSchemaVersion.DRAFT4,
        #         title="errorResponse",
        #         type=apigateway.JsonSchemaType.OBJECT,
        #         properties={
        #             "state": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING),
        #             "message": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING)
        #         }
        #     )
        # )

        # users.add_method("GET", okta_request_integration,
        #     # We can mark the parameters as required
        #     request_parameters={
        #         "method.request.querystring.who": True
        #     },
        #     # we can set request validator options like below
        #     request_validator_options=apigateway.RequestValidatorOptions(
        #         request_validator_name="test-validator",
        #         validate_request_body=True,
        #         validate_request_parameters=False
        #     ),
        #     method_responses=[apigateway.MethodResponse(
        #         # Successful response from the integration
        #         status_code="200",
        #         # Define what parameters are allowed or not
        #         response_parameters={
        #             "method.response.header.Content-Type": True,
        #             "method.response.header.Access-Control-Allow-Origin": True,
        #             "method.response.header.Access-Control-Allow-Credentials": True
        #         },
        #         # Validate the schema on the response
        #         response_models={
        #             "application/json": response_model
        #         }
        #     ), apigateway.MethodResponse(
        #         # Same thing for the error responses
        #         status_code="400",
        #         response_parameters={
        #             "method.response.header.Content-Type": True,
        #             "method.response.header.Access-Control-Allow-Origin": True,
        #             "method.response.header.Access-Control-Allow-Credentials": True
        #         },
        #         response_models={
        #             "application/json": error_response_model
        #         }
        #     )
        #     ]
        # )