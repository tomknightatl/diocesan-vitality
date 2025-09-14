import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Container, Table, Spinner, Alert, Pagination, Form, Row, Col, OverlayTrigger, Tooltip } from 'react-bootstrap';

function ParishList({ dioceseId }) {
  const [parishes, setParishes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(20);
  const [totalParishes, setTotalParishes] = useState(0);
  const [sortBy, setSortBy] = useState('Name');
  const [sortOrder, setSortOrder] = useState('asc');

  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const initialFilter = queryParams.get('filter') || '';

  const [filterName, setFilterName] = useState('');
  const [filterAddress, setFilterAddress] = useState('');
  const [filterWebsite, setFilterWebsite] = useState('');
  const [filterDataExtracted, setFilterDataExtracted] = useState(initialFilter === 'with_data' ? 'true' : '');

  const [debouncedFilterName, setDebouncedFilterName] = useState(filterName);
  const [debouncedFilterAddress, setDebouncedFilterAddress] = useState(filterAddress);
  const [debouncedFilterWebsite, setDebouncedFilterWebsite] = useState(filterWebsite);
  const [debouncedFilterDataExtracted, setDebouncedFilterDataExtracted] = useState(filterDataExtracted);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedFilterName(filterName);
      setDebouncedFilterAddress(filterAddress);
      setDebouncedFilterWebsite(filterWebsite);
      setDebouncedFilterDataExtracted(filterDataExtracted);
    }, 500);

    return () => {
      clearTimeout(handler);
    };
  }, [filterName, filterAddress, filterWebsite, filterDataExtracted]);

  useEffect(() => {
    const fetchParishes = async () => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams({
          page: currentPage,
          page_size: itemsPerPage,
          sort_by: sortBy,
          sort_order: sortOrder,
        });

        if (debouncedFilterName) params.append('filter_name', debouncedFilterName);
        if (debouncedFilterAddress) params.append('filter_address', debouncedFilterAddress);
        if (debouncedFilterWebsite) params.append('filter_website', debouncedFilterWebsite);
        if (debouncedFilterDataExtracted) params.append('filter_data_extracted', debouncedFilterDataExtracted);

        const url = dioceseId 
          ? `/api/dioceses/${dioceseId}/parishes?${params.toString()}`
          : `/api/parishes?${params.toString()}`;

        const response = await fetch(url);
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        const result = await response.json();
        if (result.error) {
          throw new Error(result.error);
        }
        setParishes(result.data);
        setTotalParishes(result.total_count);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchParishes();
  }, [currentPage, sortBy, sortOrder, debouncedFilterName, debouncedFilterAddress, debouncedFilterWebsite, debouncedFilterDataExtracted, dioceseId]);

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('asc');
    }
  };

  const totalPages = Math.ceil(totalParishes / itemsPerPage);

  let paginationItems = [];
  for (let number = 1; number <= totalPages; number++) {
    paginationItems.push(
      <Pagination.Item key={number} active={number === currentPage} onClick={() => setCurrentPage(number)}>
        {number}
      </Pagination.Item>,
    );
  }

  const renderTooltip = (props, text) => (
    <Tooltip id="button-tooltip" {...props}>
      {text}
    </Tooltip>
  );

  const renderBlockingTooltip = (props, parish) => {
    if (!parish.is_blocked) {
      return (
        <Tooltip id="blocking-tooltip" {...props}>
          <div>
            <strong>✅ Accessible</strong><br />
            Status: {parish.status_description}<br />
            HTTP Status: {parish.status_code || 'N/A'}<br />
            Respectful Automation: ✅
          </div>
        </Tooltip>
      );
    }

    return (
      <Tooltip id="blocking-tooltip" {...props}>
        <div>
          <strong>🚫 BLOCKED</strong><br />
          <strong>Type:</strong> {parish.blocking_type}<br />
          <strong>Status:</strong> {parish.status_description}<br />
          <strong>HTTP Status:</strong> {parish.status_code || 'N/A'}<br />
          {parish.blocking_evidence?.robots_txt && (
            <>
              <strong>Robots.txt:</strong> {parish.blocking_evidence.robots_txt}<br />
            </>
          )}
          {parish.blocking_evidence?.evidence_list?.length > 0 && (
            <>
              <strong>Evidence:</strong> {parish.blocking_evidence.evidence_list.join(', ')}<br />
            </>
          )}
          {parish.robots_txt_check?.robots_url && (
            <>
              <strong>Robots URL:</strong> {parish.robots_txt_check.robots_url}
            </>
          )}
        </div>
      </Tooltip>
    );
  };

  return (
    <Container className="mt-4">
      <h2>{dioceseId ? 'Parishes in Diocese' : 'All Parishes'}</h2>
      {loading && <Spinner animation="border" />}
      {error && <Alert variant="danger">Error fetching parishes: {error}</Alert>}
      {!loading && !error && (
        <Table striped bordered hover responsive>
          <thead>
            <tr>
              <th style={{ cursor: 'pointer' }}>
                <div onClick={() => handleSort('Name')}>
                  Name {sortBy === 'Name' && (sortOrder === 'asc' ? '▲' : '▼')}
                </div>
                <Form.Control
                  type="text"
                  placeholder="Filter Name"
                  value={filterName}
                  onChange={(e) => setFilterName(e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  className="mt-1"
                />
              </th>
              <th style={{ cursor: 'pointer' }}>
                <div onClick={() => handleSort('Street Address')}>
                  Address {sortBy === 'Street Address' && (sortOrder === 'asc' ? '▲' : '▼')}
                </div>
                <Form.Control
                  type="text"
                  placeholder="Filter Address"
                  value={filterAddress}
                  onChange={(e) => setFilterAddress(e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  className="mt-1"
                />
              </th>
              <th style={{ cursor: 'pointer' }}>
                <div onClick={() => handleSort('Web')}>
                  Website {sortBy === 'Web' && (sortOrder === 'asc' ? '▲' : '▼')}
                </div>
                <Form.Control
                  type="text"
                  placeholder="Filter Website"
                  value={filterWebsite}
                  onChange={(e) => setFilterWebsite(e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  className="mt-1"
                />
              </th>
              <th style={{ cursor: 'pointer', width: '120px', minWidth: '120px' }}>
                <div onClick={() => handleSort('data_extracted')}>
                  Data Extracted {sortBy === 'data_extracted' && (sortOrder === 'asc' ? '▲' : '▼')}
                </div>
                <Form.Select
                  value={filterDataExtracted}
                  onChange={(e) => setFilterDataExtracted(e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  className="mt-1"
                >
                  <option value="">All</option>
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </Form.Select>
              </th>
              <th style={{ cursor: 'pointer', width: '100px', minWidth: '100px' }} onClick={() => handleSort('is_blocked')}>
                Blocked {sortBy === 'is_blocked' && (sortOrder === 'asc' ? '▲' : '▼')}
              </th>
              <th style={{ width: '120px', minWidth: '120px' }}>Schedules</th>
            </tr>
          </thead>
          <tbody>
            {parishes.map((parish, index) => (
              <tr key={parish.id || index}>
                <td>{parish.Name}</td>
                <td>{parish.Address}</td>
                <td><a href={parish.Website} target="_blank" rel="noopener noreferrer">{parish.Website}</a></td>
                <td>{parish.data_extracted ? 'Yes' : 'No'}</td>
                <td>
                  {parish.respectful_automation_used ? (
                    <OverlayTrigger
                      placement="top"
                      delay={{ show: 250, hide: 400 }}
                      overlay={(props) => renderBlockingTooltip(props, parish)}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <input
                          type="checkbox"
                          checked={parish.is_blocked || false}
                          readOnly
                          style={{
                            cursor: parish.is_blocked ? 'help' : 'default',
                            accentColor: parish.is_blocked ? '#dc3545' : '#28a745'
                          }}
                        />
                      </div>
                    </OverlayTrigger>
                  ) : (
                    <span style={{ color: '#6c757d', fontSize: '0.8em' }}>Not tested</span>
                  )}
                </td>
                <td>
                  <Link to={`/parish?id=${parish.id}`}>View Schedules</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {!loading && !error && totalPages > 1 && (
        <div className="d-flex justify-content-center mt-3">
          <Pagination>
            <Pagination.Prev onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))} disabled={currentPage === 1} />
            {paginationItems}
            <Pagination.Next onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))} disabled={currentPage === totalPages} />
          </Pagination>
        </div>
      )}
    </Container>
  );
}

export default ParishList;