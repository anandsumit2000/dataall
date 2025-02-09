from dataall.base.context import get_context
from dataall.base.db import exceptions
from dataall.core.activity.db.activity_models import Activity
from dataall.core.environment.db.environment_repositories import EnvironmentRepository
from dataall.core.organizations.db.organization_repositories import OrganizationRepository
from dataall.core.organizations.services.organizations_enums import OrganisationUserRole
from dataall.core.organizations.db.organization_models import OrganizationGroup
from dataall.core.organizations.db import organization_models as models
from dataall.core.permissions import permissions
from dataall.core.permissions.permission_checker import has_tenant_permission, has_resource_permission
from dataall.core.permissions.db.resource_policy_repositories import ResourcePolicy


class OrganizationService:
    """Service that serves request related to organization"""

    @staticmethod
    @has_tenant_permission(permissions.MANAGE_ORGANIZATIONS)
    def create_organization(data):
        context = get_context()
        with context.db_engine.scoped_session() as session:
            username = context.username
            org = models.Organization(
                label=data.get('label'),
                owner=username,
                tags=data.get('tags', []),
                description=data.get('description', 'No description provided'),
                SamlGroupName=data.get('SamlGroupName'),
                userRoleInOrganization=OrganisationUserRole.Owner.value,
            )
            session.add(org)
            session.commit()

            member = models.OrganizationGroup(
                organizationUri=org.organizationUri,
                groupUri=data['SamlGroupName'],
            )
            session.add(member)

            activity = Activity(
                action='org:create',
                label='org:create',
                owner=username,
                summary=f'{username} create organization {org.name} ',
                targetUri=org.organizationUri,
                targetType='org',
            )
            session.add(activity)

            ResourcePolicy.attach_resource_policy(
                session=session,
                group=data['SamlGroupName'],
                permissions=permissions.ORGANIZATION_ALL,
                resource_uri=org.organizationUri,
                resource_type=models.Organization.__name__,
            )

            return org

    @staticmethod
    @has_resource_permission(permissions.UPDATE_ORGANIZATION)
    def update_organization(uri, data):
        context = get_context()
        with context.db_engine.scoped_session() as session:
            organization = OrganizationRepository.get_organization_by_uri(session, uri)
            for field in data.keys():
                setattr(organization, field, data.get(field))
            session.commit()

            activity = Activity(
                action='org:update',
                label='org:create',
                owner=context.username,
                summary=f'{context.username} updated organization {organization.name} ',
                targetUri=organization.organizationUri,
                targetType='org',
            )
            session.add(activity)
            ResourcePolicy.attach_resource_policy(
                session=session,
                group=organization.SamlGroupName,
                permissions=permissions.ORGANIZATION_ALL,
                resource_uri=organization.organizationUri,
                resource_type=models.Organization.__name__,
            )
            return organization

    @staticmethod
    @has_resource_permission(permissions.GET_ORGANIZATION)
    def get_organization(uri):
        context = get_context()
        with context.db_engine.scoped_session() as session:
            return OrganizationRepository.get_organization_by_uri(
                session=session, uri=uri
            )

    @staticmethod
    def list_organizations(filter):
        context = get_context()
        with context.db_engine.scoped_session() as session:
            return OrganizationRepository.paginated_user_organizations(
                session=session,
                data=filter,
            )

    @staticmethod
    @has_resource_permission(permissions.GET_ORGANIZATION)
    def list_organization_environments(filter, uri):
        context = get_context()
        with context.db_engine.scoped_session() as session:
            return OrganizationRepository.paginated_organization_environments(
                session=session,
                uri=uri,
                data=filter,
            )

    @staticmethod
    def count_organization_resources(uri, group):
        context = get_context()
        with context.db_engine.scoped_session() as session:
            environments = EnvironmentRepository.count_environments_with_organization_uri(
                session=session, uri=uri
            )

            groups = OrganizationRepository.count_organization_invited_groups(
                session=session, uri=uri, group=group
            )

            return {'environments': environments, 'groups': groups, 'users': 0}

    @staticmethod
    def resolve_user_role(organization):
        context = get_context()
        if organization.owner == context.username:
            return OrganisationUserRole.Owner.value
        elif organization.SamlGroupName in context.groups:
            return OrganisationUserRole.Admin.value
        else:
            with context.db_engine.scoped_session() as session:
                if OrganizationRepository.find_organization_membership(
                        session=session, uri=organization.organizationUri, groups=context.groups
                ):
                    return OrganisationUserRole.Invited.value
        return OrganisationUserRole.NoPermission.value

    @staticmethod
    @has_tenant_permission(permissions.MANAGE_ORGANIZATIONS)
    @has_resource_permission(permissions.DELETE_ORGANIZATION)
    def archive_organization(uri):
        context = get_context()
        with context.db_engine.scoped_session() as session:
            org = OrganizationRepository.get_organization_by_uri(session, uri)
            environments = EnvironmentRepository.count_environments_with_organization_uri(session, uri)
            if environments:
                raise exceptions.UnauthorizedOperation(
                    action='ARCHIVE_ORGANIZATION',
                    message='The organization you tried to delete has linked environments',
                )
            session.delete(org)
            ResourcePolicy.delete_resource_policy(
                session=session,
                group=org.SamlGroupName,
                resource_uri=org.organizationUri,
                resource_type=models.Organization.__name__,
            )

            return True

    @staticmethod
    @has_tenant_permission(permissions.MANAGE_ORGANIZATIONS)
    @has_resource_permission(permissions.INVITE_ORGANIZATION_GROUP)
    def invite_group(uri, data):
        context = get_context()
        with context.db_engine.scoped_session() as session:
            group: str = data['groupUri']

            organization = OrganizationRepository.get_organization_by_uri(session, uri)

            group_membership = OrganizationRepository.find_group_membership(session, group, organization)
            if group_membership:
                raise exceptions.UnauthorizedOperation(
                    action='INVITE_TEAM',
                    message=f'Team {group} is already admin of the organization {organization.name}',
                )
            org_group = OrganizationGroup(
                organizationUri=organization.organizationUri,
                groupUri=group,
                invitedBy=context.username,
            )
            session.add(org_group)
            ResourcePolicy.attach_resource_policy(
                session=session,
                group=group,
                resource_uri=organization.organizationUri,
                permissions=permissions.ORGANIZATION_INVITED,
                resource_type=models.Organization.__name__,
            )

            return organization

    @staticmethod
    @has_tenant_permission(permissions.MANAGE_ORGANIZATIONS)
    @has_resource_permission(permissions.REMOVE_ORGANIZATION_GROUP)
    def remove_group(uri, group):
        context = get_context()
        with context.db_engine.scoped_session() as session:
            organization = OrganizationRepository.get_organization_by_uri(session, uri)

            if group == organization.SamlGroupName:
                raise exceptions.UnauthorizedOperation(
                    action='REMOVE_TEAM',
                    message=f'Team: {group} is the owner of the organization {organization.name}',
                )

            group_env_objects_count = EnvironmentRepository.count_environments_with_organization_and_group(
                session=session,
                organization=organization,
                group=group
            )
            if group_env_objects_count > 0:
                raise exceptions.OrganizationResourcesFound(
                    action='Remove Team',
                    message=f'Team: {group} has {group_env_objects_count} linked environments on this environment.',
                )

            group_membership = OrganizationRepository.find_group_membership(session, group, organization)
            if group_membership:
                session.delete(group_membership)
                session.commit()

            ResourcePolicy.delete_resource_policy(
                session=session,
                group=group,
                resource_uri=organization.organizationUri,
                resource_type=models.Organization.__name__,
            )
            return organization

    @staticmethod
    @has_resource_permission(permissions.GET_ORGANIZATION)
    def list_organization_groups(filter, uri):
        context = get_context()
        with context.db_engine.scoped_session() as session:
            return OrganizationRepository.paginated_organization_groups(
                session=session,
                uri=uri,
                data=filter,
            )

    @staticmethod
    def resolve_organization_by_env(uri):
        context = get_context()
        with context.db_engine.scoped_session() as session:
            env = EnvironmentRepository.get_environment_by_uri(session, uri)
            return OrganizationRepository.find_organization_by_uri(session, env.organizationUri)
