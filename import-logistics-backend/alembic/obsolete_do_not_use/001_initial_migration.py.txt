# alembic/versions/001_initial_migration.py
"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('first_name', sa.String(), nullable=False),
        sa.Column('last_name', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=True),
        sa.Column('role', sa.Enum('admin', 'manager', 'clerk', 'viewer', name='userrole'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # Create containers table
    op.create_table('containers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('container_type', sa.Enum('20ft', '40ft', name='containertype'), nullable=False),
        sa.Column('msc_container_number', sa.String(), nullable=True),
        sa.Column('allocation_method', sa.Enum('weight_based', 'value_based', name='allocationmethod'), nullable=True),
        sa.Column('allocation_override', sa.Boolean(), nullable=True),
        sa.Column('is_sealed', sa.Boolean(), nullable=True),
        sa.Column('is_shipped', sa.Boolean(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_containers_id'), 'containers', ['id'], unique=False)
    op.create_index(op.f('ix_containers_msc_container_number'), 'containers', ['msc_container_number'], unique=True)

    # Create container_expenses table
    op.create_table('container_expenses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('container_id', sa.Integer(), nullable=False),
        sa.Column('expense_type', sa.Enum('loading_fee', 'shipping_fee', 'clearing_fee', 'offloading_fee', 'warehouse_fee', 'security_fee', 'extra_fee', name='expensetype'), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('fx_rate_to_usd', sa.Float(), nullable=False),
        sa.Column('amount_usd', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['container_id'], ['containers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_container_expenses_id'), 'container_expenses', ['id'], unique=False)

    # Create items table
    op.create_table('items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('container_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('category', sa.Enum('electronics', 'vehicles', 'engines', 'appliances', 'food_items', 'laptops', 'other', name='itemcategory'), nullable=False),
        sa.Column('condition', sa.Enum('new', 'tokunbo', 'used', name='itemcondition'), nullable=False),
        sa.Column('purchase_price', sa.Float(), nullable=False),
        sa.Column('purchase_currency', sa.String(length=3), nullable=False),
        sa.Column('purchase_date', sa.String(), nullable=True),
        sa.Column('fx_rate_to_usd', sa.Float(), nullable=False),
        sa.Column('purchase_price_usd', sa.Float(), nullable=False),
        sa.Column('weight', sa.Float(), nullable=False),
        sa.Column('volume', sa.Float(), nullable=True),
        sa.Column('allocated_cost', sa.Float(), nullable=True),
        sa.Column('landed_cost', sa.Float(), nullable=True),
        sa.Column('recommended_price', sa.Float(), nullable=True),
        sa.Column('selling_price', sa.Float(), nullable=True),
        sa.Column('sold', sa.Boolean(), nullable=True),
        sa.Column('sold_date', sa.String(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['container_id'], ['containers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_items_id'), 'items', ['id'], unique=False)

    # Create price_records table
    op.create_table('price_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('method', sa.Enum('cost_based', 'market_based', 'last_sold', name='pricingmethod'), nullable=False),
        sa.Column('source', sa.Enum('jiji', 'ebay', 'mobile_de', 'autoscout24', 'bazos_cz', name='pricingsource'), nullable=True),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('source_data', sa.JSON(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('margin_percentage', sa.Float(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['item_id'], ['items.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_price_records_id'), 'price_records', ['id'], unique=False)

    # Create tracking_records table
    op.create_table('tracking_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('container_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('booked', 'gate_in', 'loaded', 'departed', 'in_transit', 'arrived', 'discharged', 'gate_out', 'delivered', name='trackingstatus'), nullable=False),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('vessel_name', sa.String(), nullable=True),
        sa.Column('voyage_number', sa.String(), nullable=True),
        sa.Column('status_date', sa.DateTime(), nullable=True),
        sa.Column('estimated_arrival', sa.DateTime(), nullable=True),
        sa.Column('actual_arrival', sa.DateTime(), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('notification_sent', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['container_id'], ['containers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tracking_records_id'), 'tracking_records', ['id'], unique=False)


def downgrade():
    # Drop tables in reverse order
    op.drop_index(op.f('ix_tracking_records_id'), table_name='tracking_records')
    op.drop_table('tracking_records')
    
    op.drop_index(op.f('ix_price_records_id'), table_name='price_records')
    op.drop_table('price_records')
    
    op.drop_index(op.f('ix_items_id'), table_name='items')
    op.drop_table('items')
    
    op.drop_index(op.f('ix_container_expenses_id'), table_name='container_expenses')
    op.drop_table('container_expenses')
    
    op.drop_index(op.f('ix_containers_msc_container_number'), table_name='containers')
    op.drop_index(op.f('ix_containers_id'), table_name='containers')
    op.drop_table('containers')
    
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS trackingstatus')
    op.execute('DROP TYPE IF EXISTS pricingsource')
    op.execute('DROP TYPE IF EXISTS pricingmethod')
    op.execute('DROP TYPE IF EXISTS itemcondition')
    op.execute('DROP TYPE IF EXISTS itemcategory')
    op.execute('DROP TYPE IF EXISTS expensetype')
    op.execute('DROP TYPE IF EXISTS allocationmethod')
    op.execute('DROP TYPE IF EXISTS containertype')
    op.execute('DROP TYPE IF EXISTS userrole')
