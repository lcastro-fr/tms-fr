import json
import logging
from typing import Any, Dict

import httpx
from lxml import etree

from lib.sap.ports.sap_ports import SAPProtocol


class Saponoso(SAPProtocol):
    """
    SAP on OSO (Orchestrated SOAP Operations)
    Encapsulates SAP SOAP RFC calling and parses responses into Python dictionaries.
    """

    def __init__(self, endpoint: str, username: str, password: str, **kwargs):
        self.endpoint = str(endpoint)
        self.username = str(username)
        self.password = str(password)
        self.introspect = kwargs.get("introspect", False)
        self.pretty_xml = kwargs.get("pretty_xml", False)
        self.debug = kwargs.get("debug", False)
        self.verify_ssl = kwargs.get("verify_ssl", False)
        self.timeout = kwargs.get("timeout", 10.0)
        self.logger = logging.getLogger("Saponoso")

    def call_rfc(self, rfc_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call the SAP RFC via SOAP and parse the response."""
        soap_envelope = self._build_soap_envelope(rfc_name, params)
        if self.debug:
            self.logger.debug(f"Calling RFC '{rfc_name}' with params: {params}")
            self.logger.debug(f"SOAP Envelope:\n{soap_envelope}")

        headers = {"Content-Type": "text/xml; charset=utf-8"}
        try:
            with httpx.Client(timeout=self.timeout, verify=self.verify_ssl) as client:
                response = client.post(
                    self.endpoint,
                    content=soap_envelope.encode("utf-8"),
                    headers=headers,
                    auth=(self.username, self.password),
                )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            self.logger.error(f"HTTP Error: {exc.response.status_code} for URL: {exc.request.url}")
            self.logger.error(f"Verbose Response Body: {exc.response.text}")
        if self.debug:
            self.logger.debug(f"RFC call executed successfully.\n{response.text}")
        return self._parse_response(response.text)

    def _build_soap_envelope(self, rfc_name: str, params: Dict[str, Any]) -> str:
        """Builds a SOAP envelope for the RFC call."""
        param_xml = "".join(f"<{k}>{v}</{k}>" for k, v in params.items())

        return f"""<?xml version="1.0"?>
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:urn="urn:sap-com:document:sap:rfc:functions">
            <soapenv:Body>

                {self._dict_to_soap_body_element(rfc_name, params)}

            </soapenv:Body>
        </soapenv:Envelope>
        """

    def _dict_to_soap_body_element(self, tag, data, namespace=None):
        """
        Recursively converts a dictionary into an XML element suitable for SOAP body insertion.

        Args:
            tag (str): The root tag name for the SOAP operation (e.g., 'RFC_READ_TABLE').
            data (dict): The input dictionary to convert.
            namespace (str): Optional namespace URI to apply to all tags.

        Returns:
            lxml.etree.Element: The root XML element.
        """
        ns = f"{{{namespace}}}" if namespace else ""

        def build_element(parent, key, value):
            if isinstance(value, dict):
                elem = etree.SubElement(parent, f"{ns}{key}")
                for k, v in value.items():
                    build_element(elem, k, v)
            elif isinstance(value, list):
                list_container = etree.SubElement(parent, f"{ns}{key}")
                for item in value:
                    item_elem = etree.SubElement(list_container, "item")
                    if isinstance(item, dict):
                        for k, v in item.items():
                            build_element(item_elem, k, v)
                    else:
                        item_elem.text = str(item)
            else:
                elem = etree.SubElement(parent, f"{ns}{key}")
                elem.text = str(value)

        NS_RFC = "urn:sap-com:document:sap:rfc:functions"
        nsmap = {"urn": NS_RFC}

        root = etree.Element(f"{{urn:sap-com:document:sap:rfc:functions}}{tag}", nsmap=nsmap)

        for k, v in data.items():
            build_element(root, k, v)

        return etree.tostring(root, pretty_print=True, encoding="unicode")

    def _parse_response(self, xml_text: str):
        """Parse all response variables from SOAP XML and decode payloads. Handles tables as lists of dicts."""
        tree = etree.fromstring(xml_text.encode("utf-8"))
        if self.pretty_xml:
            self.logger.debug("--- Raw XML Response --------------------------------")
            self.logger.debug(xml_text.replace("><", ">\n<"))
            self.logger.debug("-^^ Raw XML Response ^^------------------------------")
        body = tree.find(".//{http://schemas.xmlsoap.org/soap/envelope/}Body")
        if body is None:
            raise ValueError("No <SOAP-ENV:Body> found in response.")

        # Find the RFC response element (first child of Body)
        rfc_response = next(body.iterchildren(), None)
        if rfc_response is None:
            raise ValueError("No RFC response element found in SOAP Body.")
        results = {}
        for var_elem in rfc_response.iterchildren():
            var_name = etree.QName(var_elem).localname
            # If the variable has children and all are <item>, treat as table
            if len(var_elem) and all(
                etree.QName(child).localname == "item" for child in var_elem.iterchildren()
            ):
                table = []
                for item in var_elem.iterchildren():
                    row = {}
                    for col in item.iterchildren():
                        col_key = etree.QName(col).localname
                        col_val = col.text.strip() if col.text and col.text.strip() else None
                        row[col_key] = (
                            self._decode_payload(col_val) if col_val is not None else None
                        )
                    table.append(row)
                results[var_name] = {"type": "table", "value": table}
            elif len(var_elem):
                # Structure or nested elements
                sub_results = {}
                for sub_elem in var_elem.iterchildren():
                    sub_key = etree.QName(sub_elem).localname
                    if sub_elem.text is None or not sub_elem.text.strip():
                        sub_parsed_val = None
                        sub_type = "NoneType"
                    else:
                        sub_text_val = sub_elem.text.strip()
                        sub_parsed_val = self._decode_payload(sub_text_val)
                        sub_type = type(sub_parsed_val).__name__
                    sub_results[sub_key] = {"type": sub_type, "value": sub_parsed_val}
                results[var_name] = sub_results
            else:
                # Scalar value
                if var_elem.text is None or not var_elem.text.strip():
                    parsed_val = None
                    val_type = "NoneType"
                else:
                    text_val = var_elem.text.strip()
                    parsed_val = self._decode_payload(text_val)
                    val_type = type(parsed_val).__name__
                results[var_name] = {"type": val_type, "value": parsed_val}
        if self.introspect:
            self.logger.debug("--- Introspection ---")
            for k, v in results.items():
                self.logger.debug(f"Variable: {k}")
                if isinstance(v, dict) and "type" in v and "value" in v:
                    self.logger.debug(f"  Type: {v['type']}")
                    self.logger.debug(f"  Value: {repr(v['value'])}\n")
                elif isinstance(v, list):
                    self.logger.debug(f"  Table with {len(v)} rows")
                    for i, row in enumerate(v):
                        self.logger.debug(f"    Row {i}: {row}")
                else:
                    for sub_k, sub_v in v.items():
                        self.logger.debug(f"  Sub-variable: {sub_k}")
                        self.logger.debug(f"    Type: {sub_v['type']}")
                        self.logger.debug(f"    Value: {repr(sub_v['value'])}\n")
        return results

    def _decode_payload(self, val: str) -> Any:
        try:
            parsed = json.loads(val)
            return parsed
        except Exception:
            pass
        if val.isdigit():
            return int(val)
        try:
            float_val = float(val)
            return float_val
        except Exception:
            pass
        return val
