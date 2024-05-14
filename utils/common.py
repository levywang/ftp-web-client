import ldap, os
from ldap3 import Server, Connection, ALL, NTLM, ALL_ATTRIBUTES
from .config import Config


# Initialize configuration
utils_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(utils_dir, '..'))
config_path = os.path.join(root_dir, "config.json")
config = Config(config_path)
ldap_config = config.get('ldap')
ldap3_config = config.get('ldap3')


class Common:
    """
    Common class providing LDAP authentication methods.
    """

    # LDAP authentication using the ldap library
    def ldap_auth(self, username, password):
        """
        Authenticate a user with the ldap library.

        Args:
        - username: The user's username.
        - password: The user's password.

        Returns:
        - True if authentication succeeds, False otherwise.
        """
        # Retrieve LDAP server information from the configuration
        ldap_server_url = ldap_config.get('server')
        ldap_bind_dn = ldap_config.get('dn')
        ldap_bind_password = ldap_config.get('password')
        search_base = ldap_config.get('search_base')

        try:
            # Establish an LDAP connection and bind with the administrative account
            ldapconn = ldap.initialize(ldap_server_url)
            ldapconn.simple_bind_s(ldap_bind_dn, ldap_bind_password)

            # Set search scope and filter, then search for the user
            searchScope = ldap.SCOPE_SUBTREE
            searchFilter = "(sAMAccountName=%s)" % username
            ldap_result = ldapconn.search_s(search_base, searchScope, searchFilter, None)

            # If search result exists, attempt to bind with the provided password for validation
            if ldap_result:
                user_dn = ldap_result[0][0]
                try:
                    ldapconn.simple_bind_s(user_dn, password)
                    return True
                except ldap.LDAPError:
                    return False
            else:
                return False
        except ldap.LDAPError:
            return False

    # LDAP authentication using the ldap3 library
    def ldap3_auth(self, username, password):
        """
        Authenticate a user with the ldap3 library.

        Args:
        - username: The user's username.
        - password: The user's password.

        Returns:
        - True if authentication succeeds, False otherwise.
        """
        # Retrieve LDAP server information from the configuration
        ldap3_server_url = ldap3_config.get('server')
        ldap3_server_port = ldap3_config.get('port')
        ldap3_domain = ldap3_config.get('domain')

        # Set up the LDAP server and attempt to bind with the user credentials automatically
        server = Server(ldap3_server_url, get_info=ALL, use_ssl=False, port=ldap3_server_port)
        try:
            conn = Connection(server, user=f"{ldap3_domain}\\{username}", password=password, authentication=NTLM, auto_bind=True)
            return True
        except Exception as e:
            return False

        # Close the connection if it was successfully established
        if conn:
            conn.unbind()