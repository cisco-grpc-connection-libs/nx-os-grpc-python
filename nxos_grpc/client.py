"""Copyright 2019 Cisco Systems

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
"""NX-OS gRPC Python wrapper library
Function usage derived from example NX-OS client from Kyoung Yun. Thanks :)
TODO: Write session state management wrapper.
TODO: Make individual returns more useful?
TODO: Exception classes.
"""
import logging
import json

try:
    # Python 3
    from urllib.parse import urlparse
except ImportError:
    # Python 2
    from urlparse import urlparse
import grpc
from .response import build_response
from . import proto


class Client(object):
    """NX-OS gRPC wrapper client to ease usage of gRPC.

    Returns relatively raw response data. Response data may be accessed
    via the ReqID, YangData, and Errors attributes/items.

    Attributes
    ----------
    username : str
    password : str
    timeout : uint

    Methods
    -------
    get(...)
        Get oper and config data.
    get_config(...)
        Get only config data.
    get_oper(...)
        Get only oper data.
    edit_config(...)
        Edit running config.
    start_session(...)
        Start stateful session for editing config, etc.
    close_session(...)
        Gracefully close stateful session.
    kill_session(...)
        Forcefully terminate stateful session.

    Examples
    --------
    >>> from nxos_grpc import Client
    >>> client = Client('127.0.0.1', 'demo', 'demo')
    >>> oper_response = client.get_oper('Cisco-NX-OS-device:System',
    ...     namespace='http://cisco.com/ns/yang/cisco-nx-os-device'
    ... )
    >>> oper_response.YangData
    ...
    >>> oper_response['YangData']
    ...
    >>> oper_response
    <nxos_grpc.response.gRPCResponse object at 0x10ebcbe80>
    >>> oper_response.as_dict()
    ...
    """

    """Defining property due to gRPC timeout being based on a C long type.
    Should really define this based on architecture.
    32-bit C long max value. "Infinity".
    """
    __C_MAX_LONG = 2147483647

    def __init__(
        self,
        target,
        username,
        password,
        timeout=__C_MAX_LONG,
        credentials=None,
        credentials_from_file=False,
        tls_server_override=None,
    ):
        """Initializes the gRPC client stub and defines authentication and timeout attributes.

        Parameters
        ----------
        target : str
            The host[:port] to issue gRPC requests against.
        username : str
        password : str
        timeout : uint, optional
            Timeout for request which sets a deadline for return.
            Defaults to "infinity"
        credentials : str, optional
            PEM contents or PEM file path.
        credentials_from_file : bool, optional
            Indicates that credentials is a file path.
        tls_server_override : str, optional
            TLS server name, if desired.
        """
        self.username = username
        self.password = password
        self.timeout = int(timeout)
        self.__target = self.__gen_target(target)
        self.__credentials = self.__gen_credentials(credentials, credentials_from_file)
        self.__options = self.__gen_options(tls_server_override)
        self.__client = self.__gen_client(
            self.__target, self.__credentials, self.__options
        )

    def __repr__(self):
        """JSON dump a dict of basic attributes."""
        return json.dumps(
            {
                "target": self.__target,
                "is_secure": True if self.__credentials else False,
                "username": self.username,
                "password": self.password,
                "timeout": self.timeout,
            }
        )

    def __gen_metadata(self):
        """Generates expected gRPC call metadata."""
        return [("username", self.username), ("password", self.password)]

    def __fulfill_request(self, request_method, request_args):
        """Generically executes a gRPC RPC "request".
        All requests follow the same control flow, thus generalization.

        Parameters
        ----------
        request_method : def
            Method to execute.
        request_args : object
            Arguments to RPC method to execute.

        Returns
        -------
        gRPCResponse
            Response wrapper object with ReqID, YangData, and Errors fields.
        """
        return build_response(
            request_args.ReqID,
            request_method(
                request_args, timeout=self.timeout, metadata=self.__gen_metadata()
            ),
        )

    def get_oper(self, yang_path, namespace=None, request_id=0, path_is_payload=False):
        """Get operational data from device.

        Parameters
        ----------
        yang_path : str
            YANG XPath which locates the datapoints.
        namespace : str, optional
            YANG namespace applicable to the specified XPath.
        request_id : uint, optional
            The request ID to indicate to the device.
        path_is_payload : bool, optional
            Indicates that the yang_path parameter contains a preformed JSON
            payload and should not be parsed into JSON as an XPath.

        Returns
        -------
        gRPCResponse
            Response wrapper object with ReqID, YangData, and Errors fields.
        """
        if not path_is_payload:
            yang_path = self.__parse_xpath_to_json(yang_path, namespace)
        request_args = proto.GetOperArgs(ReqID=request_id, YangPath=yang_path)
        return self.__fulfill_request(
            request_method=self.__client.GetOper, request_args=request_args
        )

    def get(self, yang_path, namespace=None, request_id=0, path_is_payload=False):
        """Get configuration and operational data from device.

        Parameters
        ----------
        yang_path : str
            YANG XPath which locates the datapoints.
        namespace : str, optional
            YANG namespace applicable to the specified XPath.
        request_id : uint, optional
            The request ID to indicate to the device.
        path_is_payload : bool, optional
            Indicates that the yang_path parameter contains a preformed JSON
            payload and should not be parsed into JSON as an XPath.

        Returns
        -------
        gRPCResponse
            Response wrapper object with ReqID, YangData, and Errors fields.
        """
        if not path_is_payload:
            yang_path = self.__parse_xpath_to_json(yang_path, namespace)
        request_args = proto.GetArgs(ReqID=request_id, YangPath=yang_path)
        return self.__fulfill_request(
            request_method=self.__client.Get, request_args=request_args
        )

    def get_config(
        self,
        yang_path,
        namespace=None,
        request_id=0,
        source="running",
        path_is_payload=False,
    ):
        """Get configuration data from device.

        Parameters
        ----------
        yang_path : str
            YANG XPath which locates the datapoints.
        namespace : str, optional
            YANG namespace applicable to the specified XPath.
        request_id : uint, optional
            The request ID to indicate to the device.
        source : { 'running', ? }, optional
            Source to retrieve configuration from.
        path_is_payload : bool, optional
            Indicates that the yang_path parameter contains a preformed JSON
            payload and should not be parsed into JSON as an XPath.

        Returns
        -------
        gRPCResponse
            Response wrapper object with ReqID, YangData, and Errors fields.

        Notes
        -----
        Need to verify whether source param may be something other than running.
        """
        self.__validate_enum_arg(source, {"running"})
        if not path_is_payload:
            yang_path = self.__parse_xpath_to_json(yang_path, namespace)
        request_args = proto.GetConfigArgs(
            ReqID=request_id, Source=source, YangPath=yang_path
        )
        return self.__fulfill_request(
            request_method=self.__client.GetConfig, request_args=request_args
        )

    def edit_config(
        self,
        yang_path,
        operation="merge",
        default_operation="merge",
        session_id=0,
        request_id=0,
        target="running",
        error_operation="roll-back",
    ):
        """Writes the specified YANG data subset to the target datastore.

        Parameters
        ----------
        yang_path : str
            JSON-encoded YANG data to be edited.
        operation : { 'merge', 'create', 'replace', 'delete', 'remove' }, optional
            Operation to perform on the configuration datastore.
        default_operation : { 'merge', 'replace', 'none' }, optional
            Default operation while traversing the configuration tree.
        session_id : uint, optional
            Unique session ID acquired from start_session.
            0 indicates stateless operation.
        request_id : uint, optional
            The request ID to indicate to the device.
        target : { 'running' }, optional
            Target datastore. Only 'running' is supported.
        error_operation : { 'roll-back', 'stop', 'continue' }, optional
            Action to be preformed in the event of an error.

        Returns
        -------
        gRPCResponse
            Response wrapper object with ReqID, YangData, and Errors fields.
        """
        self.__validate_enum_arg(
            operation, {"merge", "create", "replace", "delete", "remove"}
        )
        self.__validate_enum_arg(default_operation, {"merge", "replace", "none"})
        self.__validate_enum_arg(target, {"running"})
        self.__validate_enum_arg(error_operation, {"roll-back", "stop", "continue"})
        request_args = proto.EditConfigArgs(
            YangPath=yang_path,
            Operation=operation,
            SessionID=session_id,
            ReqID=request_id,
            Target=target,
            DefOp=default_operation,
            ErrorOp=error_operation,
        )
        return self.__fulfill_request(
            request_method=self.__client.EditConfig, request_args=request_args
        )

    def start_session(self, request_id=0):
        """Starts a new session acquiring a session ID.

        Parameters
        ----------
        request_id : uint, optional
            The request ID to indicate to the device.

        Returns
        -------
        gRPCResponse
            Response wrapper object with ReqID, YangData, and Errors fields.
        """
        request_args = proto.SessionArgs(ReqID=request_id)
        return self.__fulfill_request(
            request_method=self.__client.StartSession, request_args=request_args
        )

    def close_session(self, session_id, request_id=0):
        """Requests graceful termination of a session.

        Parameters
        ----------
        session_id : uint
            Unique session ID acquired from starting a session.
        request_id : uint, optional
            The request ID to indicate to the device.

        Returns
        -------
        gRPCResponse
            Response wrapper object with ReqID, YangData, and Errors fields.
        """
        request_args = proto.CloseSessionArgs(ReqID=request_id, SessionID=session_id)
        return self.__fulfill_request(
            request_method=self.__client.CloseSession, request_args=request_args
        )

    def kill_session(self, session_id, session_id_to_kill, request_id=0):
        """Forces the closing of a session.

        Parameters
        ----------
        session_id : uint
            Unique session ID acquired from starting a session.
        session_id_to_kill : uint
            Unique session ID to kill.
        request_id : uint, optional
            The request ID to indicate to the device.

        Returns
        -------
        gRPCResponse
            Response wrapper object with ReqID, YangData, and Errors fields.

        Notes
        -----
        Not verified on whether we need to open a new session to kill a session.
        """
        request_args = proto.KillArgs(
            ReqID=request_id, SessionID=session_id, SessionIDToKill=session_id_to_kill
        )
        return self.__fulfill_request(
            request_method=self.__client.KillSession, request_args=request_args
        )

    @staticmethod
    def __gen_target(target, netloc_prefix="//", default_port=50051):
        """Parses and validates a supplied target URL for gRPC calls.
        Uses urllib to parse the netloc property from the URL.
        netloc property is, effectively, fqdn/hostname:port.
        This provides some level of URL validation and flexibility.
        Returns netloc property of target.
        """
        if netloc_prefix not in target:
            target = netloc_prefix + target
        parsed_target = urlparse(target)
        if not parsed_target.netloc:
            raise ValueError("Unable to parse netloc from target URL %s!", target)
        if parsed_target.scheme:
            logging.debug("Scheme identified in target, ignoring and using netloc.")
        target_netloc = parsed_target.netloc
        if parsed_target.port is None:
            ported_target = "%s:%i" % (parsed_target.hostname, default_port)
            logging.debug("No target port detected, reassembled to %s.", ported_target)
            target_netloc = Client.__gen_target(ported_target)
        return target_netloc

    @staticmethod
    def __gen_client(target, credentials=None, options=None):
        """Instantiates and returns the NX-OS gRPC client stub
        over an insecure or secure channel.
        """
        client = None
        if not credentials:
            insecure_channel = grpc.insecure_channel(target)
            client = proto.gRPCConfigOperStub(insecure_channel)
        else:
            channel_creds = grpc.ssl_channel_credentials(credentials)
            secure_channel = grpc.secure_channel(target, channel_creds, options)
            client = proto.gRPCConfigOperStub(secure_channel)
        return client

    @staticmethod
    def __gen_credentials(credentials, credentials_from_file):
        """Generate credentials either by reading credentials from
        the specified file or return the original creds specified.
        """
        if not credentials:
            return None
        if credentials_from_file:
            with open(credentials, "rb") as creds_fd:
                credentials = creds_fd.read()
        return credentials

    @staticmethod
    def __gen_options(tls_server_override):
        """Generate options tuple for gRPC overrides, etc.
        Only TLS server is handled currently.
        """
        options = []
        if tls_server_override:
            options.append(("grpc.ssl_target_name_override", tls_server_override))
        return tuple(options)

    @staticmethod
    def __parse_xpath_to_json(xpath, namespace):
        """Parses an XPath to JSON representation, and appends
        namespace into the JSON request.
        """
        if not namespace:
            raise ValueError("Must include namespace if constructing from xpath!")
        xpath_dict = {}
        xpath_split = xpath.split("/")
        first = True
        for element in reversed(xpath_split):
            if first:
                xpath_dict[element] = {}
                first = False
            else:
                xpath_dict = {element: xpath_dict}
        xpath_dict["namespace"] = namespace
        return json.dumps(xpath_dict)

    @staticmethod
    def __validate_enum_arg(name, valid_options, message=None):
        """Construct error around enumeration validation."""
        if name not in valid_options:
            if not message:
                message = "%s must be one of %s" % (name, ", ".join(valid_options))
            raise ValueError(message)
