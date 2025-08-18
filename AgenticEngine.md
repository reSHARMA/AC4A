# Access Control for Github Agentic Workflows using AC4A

Access Control for Agents (AC4A) is a framework designed to provide fine-grained access control, protecting data from unauthorized access by agents. The framework offers a resource-focused permission system, where each permission is defined over a resource, and resources can be hierarchically organized. Permissions are based on read/write access patterns. To function, the framework requires a declaration of the resource hierarchy and a mapping from actual tool calls to the permissions required for those calls.

MCP already has some basic built-in access control. Servers can define resources that clients may read, such as documentation. For clients, these resources are read-only.

The MCP protocol also allows clients to define roots—starting points in the client’s file system where the server can read or write files. The server is responsible for restricting its access to these roots.

URIs for resources can be anything, but for roots, they must be strictly `file://` URIs.

The features supported by MCP are not sufficient for fine-grained access control. Ideally, the following extensions to MCP are needed to support AC4A-like access control:

1. The server must be able to share its resource hierarchy with the client, allowing the client to define permissions over resources through roots.
2. Roots must support custom URIs, not just `file://`, so that an `ac4a://` URI scheme can be used.
3. The server must be able to check access control policies defined by the client before performing any tool calls.

This approach not only requires changes in the MCP but also requires changes in the implementation of the MCP servers. To support AC4A-based access control in agentic engines like Claude-Code or Codex without requiring changes in the MCP servers, we can use a proxy server that implements the AC4A framework and acts as a bridge between the MCP client and the MCP server. The proxy server will handle the access control policies and enforce them before forwarding the requests to the MCP server.

GitHub Agentic workflows are an example of an abstraction over agentic engines like Claude-Code or Codex. The agentic workflow allows users to define workflows that can be executed by the agentic engines. The GitHub Agentic workflow can be extended to support AC4A-based access control by allowing users to define permissions over the resources used in the workflows. The permissions can be defined using the AC4A framework and enforced by the proxy server before executing the workflows.

## Augmented Agentic Workflow Flow with AC4A-Based Access Control

1. For every MCP server, the resource hierarchy and the mapping between the tool calls and the permissions required to perform the tool calls will be defined in the proxy server.

   **Example:**

   **Resource Hierarchy:**
   ```
   GH:Issue
   - GH:Body
   - GH:Title
   - GH:Label
   - GH:State
   - GH:Assignee
   - GH:SubIssue
   - GH:Comment
   GH:Label
   ```

   **Mapping**
   ```
   update_issue(...) based on the arguments requires the following permissions:
   - GH:Issue(id):write -> Allows updating all the fields of the issue id 
   - GH:Issue(id)::GH:Body(*):write -> Allows updating the body of the issue id  
   - GH:Issue(id)::GH:Title(*):write -> Allows updating the title of the issue id
   - GH:Issue(id)::GH:Label(*):write -> Allows updating the labels of the issue id
   - GH:Issue(id)::GH:State(*):write -> Allows updating the state of the issue id
   - GH:Issue(id)::GH:Assignee(*):write -> Allows updating the assignee of the issue id
   - GH:Issue(id)::GH:SubIssue(*):write -> Allows updating the sub-issues of the issue id
   - GH:Issue(id)::GH:Comment(*):write -> Allows updating the comments of the issue id

   search_issues(...) based on the arguments requires the following permissions:
   - GH:Issue(*):read -> Allows reading all the fields of the issue
   ```

2. In the GitHub Agentic workflow definition, the user will define the permissions granted to the agentic engine for each resource used in the workflow.

   **Example:**
   ```
   # The permissions for reading all the issues but only writing the label of the issue with id, id will be defined as follows:
   permissions:
       - ac4a://github.mcp/GH:Issue/id/GH:Label/*#write
       - ac4a://github.mcp/GH:Issue/*#read
   # Syntax:
   # ac4a://unique_mcp_name.mcp/(resource_name/resource_value/)+#[read|write]
   ```

3. When Claude-Code or Codex is initialized, it must be initialized with the proxy server as the base address. The proxy server will handle the access control policies and enforce them before forwarding the requests to the MCP server.

4. The proxy server will intercept the requests made by the agentic engine and check if the requested actions are allowed based on the defined permissions. If the action is allowed, it will forward the request to the MCP server; otherwise, it will return an error message indicating that the action is not permitted. The checking happens by first evaluating the actual arguments which are passed to the tool call. The actual required permission is extracted and matched with the active set of permissions defined by the user in the workflow.

Ideally, this all must happen inside the MCP server, but since we do not have control over the MCP servers, we need to use a proxy server to implement the AC4A framework.