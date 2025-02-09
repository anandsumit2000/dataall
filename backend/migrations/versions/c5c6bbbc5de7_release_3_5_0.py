"""release 3.5.0

Revision ID: c5c6bbbc5de7
Revises: b6e0ac8f6d3f
Create Date: 2021-11-15 08:47:40.128047

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import Boolean, Column, String, orm
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import query_expression

from dataall.base.db import Resource, utils
from dataall.core.environment.api.enums import EnvironmentPermission, EnvironmentType

# revision identifiers, used by Alembic.
revision = 'c5c6bbbc5de7'
down_revision = 'b6e0ac8f6d3f'
branch_labels = None
depends_on = None

Base = declarative_base()


class Environment(Resource, Base):
    __tablename__ = 'environment'
    organizationUri = Column(String, nullable=False)
    environmentUri = Column(String, primary_key=True, default=utils.uuid('environment'))
    AwsAccountId = Column(String, nullable=False)
    region = Column(String, nullable=False, default='eu-west-1')
    cognitoGroupName = Column(String, nullable=True)

    validated = Column(Boolean, default=False)
    environmentType = Column(String, nullable=False, default=EnvironmentType.Data.value)
    isOrganizationDefaultEnvironment = Column(Boolean, default=False)
    EnvironmentDefaultIAMRoleName = Column(String, nullable=False)
    EnvironmentDefaultIAMRoleArn = Column(String, nullable=False)
    EnvironmentDefaultBucketName = Column(String)
    roleCreated = Column(Boolean, nullable=False, default=False)

    EnvironmentDefaultIAMRoleImported = Column(Boolean, default=False)
    resourcePrefix = Column(String, nullable=False, default='dh')

    dashboardsEnabled = Column(Boolean, default=False)
    notebooksEnabled = Column(Boolean, default=True)
    mlStudiosEnabled = Column(Boolean, default=True)
    pipelinesEnabled = Column(Boolean, default=True)
    warehousesEnabled = Column(Boolean, default=True)

    userRoleInEnvironment = query_expression()

    SamlGroupName = Column(String, nullable=True)
    CDKRoleArn = Column(String, nullable=False)

    subscriptionsEnabled = Column(Boolean, default=False)
    subscriptionsProducersTopicName = Column(String)
    subscriptionsProducersTopicImported = Column(Boolean, default=False)
    subscriptionsConsumersTopicName = Column(String)
    subscriptionsConsumersTopicImported = Column(Boolean, default=False)


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'keyvaluetag',
        sa.Column('tagUri', sa.String(), nullable=False),
        sa.Column('targetUri', sa.String(), nullable=False),
        sa.Column('targetType', sa.String(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('tagUri'),
    )
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    print('Adding environment resourcePrefix...')
    op.add_column(
        'environment', sa.Column('resourcePrefix', sa.String(), nullable=False)
    )
    op.add_column(
        'environment',
        sa.Column('EnvironmentDefaultIAMRoleImported', sa.Boolean(), nullable=True),
    )
    op.add_column(
        'environment_group_permission',
        sa.Column('environmentIAMRoleImported', sa.Boolean(), nullable=True),
    )

    environments: [Environment] = session.query(Environment).all()
    for environment in environments:
        print(f'Back filling resourcePrefix to environment {environment.label}')
        environment.resourcePrefix = 'dh'
        session.commit()

    print('Successfully back filled resourcePrefix ')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('environment_group_permission', 'environmentIAMRoleImported')
    op.drop_column('environment', 'EnvironmentDefaultIAMRoleImported')
    op.drop_column('environment', 'resourcePrefix')
    op.drop_table('keyvaluetag')
    # ### end Alembic commands ###
