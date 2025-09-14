import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Container, Table, Spinner, Alert, Pagination, Form, Row, Col, OverlayTrigger, Tooltip } from 'react-bootstrap';
import ParishList from './ParishList';
import './App.css';

function App() {
  const [dioceses, setDioceses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [summary, setSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState(null);

  // State for pagination and sorting
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(20); // Fixed items per page
  const [totalDioceses, setTotalDioceses] = useState(0);
  const [sortBy, setSortBy] = useState('Name');
  const [sortOrder, setSortOrder] = useState('asc'); // 'asc' or 'desc'

  // State for per-column filtering
  const [filterName, setFilterName] = useState('');
  const [filterAddress, setFilterAddress] = useState('');
  const [filterWebsite, setFilterWebsite] = useState('');

  // State for debounced filters
  const [debouncedFilterName, setDebouncedFilterName] = useState(filterName);
  const [debouncedFilterAddress, setDebouncedFilterAddress] = useState(filterAddress);
  const [debouncedFilterWebsite, setDebouncedFilterWebsite] = useState(filterWebsite);

  // Debounce effect for filters
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedFilterName(filterName);
      setDebouncedFilterAddress(filterAddress);
      setDebouncedFilterWebsite(filterWebsite);
    }, 500); // 500ms delay

    return () => {
      clearTimeout(handler);
    };
  }, [filterName, filterAddress, filterWebsite]);

  useEffect(() => {
    const fetchDioceses = async () => {
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

        const response = await fetch(`/api/dioceses?${params.toString()}`);
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        const result = await response.json();
        if (result.error) {
          throw new Error(result.error);
        }
        setDioceses(result.data);
        setTotalDioceses(result.total_count);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchDioceses();

    // Fetch summary data
    fetch('/api/summary')
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then(data => {
        if (data.error) {
          throw new Error(data.error);
        }
        setSummary(data);
        setSummaryLoading(false);
      })
      .catch(error => {
        setSummaryError(error.message);
        setSummaryLoading(false);
      });
  }, [currentPage, sortBy, sortOrder, debouncedFilterName, debouncedFilterAddress, debouncedFilterWebsite]);

  // Function to handle sorting
  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('asc');
    }
  };

  // Calculate total pages for pagination
  const totalPages = Math.ceil(totalDioceses / itemsPerPage);

  // Generate pagination items
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

  const renderBlockingTooltip = (props, diocese) => {
    if (!diocese.is_blocked) {
      return (
        <Tooltip id="blocking-tooltip" {...props}>
          <div>
            <strong>✅ Accessible</strong><br />
            Status: {diocese.status_description}<br />
            HTTP Status: {diocese.status_code || 'N/A'}<br />
            Respectful Automation: ✅
          </div>
        </Tooltip>
      );
    }

    return (
      <Tooltip id="blocking-tooltip" {...props}>
        <div>
          <strong>🚫 BLOCKED</strong><br />
          <strong>Type:</strong> {diocese.blocking_type}<br />
          <strong>Status:</strong> {diocese.status_description}<br />
          <strong>HTTP Status:</strong> {diocese.status_code || 'N/A'}<br />
          {diocese.blocking_evidence?.robots_txt && (
            <>
              <strong>Robots.txt:</strong> {diocese.blocking_evidence.robots_txt}<br />
            </>
          )}
          {diocese.blocking_evidence?.evidence_list?.length > 0 && (
            <>
              <strong>Evidence:</strong> {diocese.blocking_evidence.evidence_list.join(', ')}<br />
            </>
          )}
          {diocese.robots_txt_check?.robots_url && (
            <>
              <strong>Robots URL:</strong> {diocese.robots_txt_check.robots_url}
            </>
          )}
        </div>
      </Tooltip>
    );
  };

  return (
    <>
      
      <Container className="mt-4">
        <h2>Data Summary</h2>
        {summaryLoading && <Spinner animation="border" />}
        {summaryError && <Alert variant="danger">Error fetching summary: {summaryError}</Alert>}
        {!summaryLoading && !summaryError && summary && (
          <div className="mb-4">
            <Row className="text-center">
              <Col>
                <OverlayTrigger
                  placement="top"
                  delay={{ show: 250, hide: 400 }}
                  overlay={(props) => renderTooltip(props, 'The total number of dioceses that have been processed to find a parish directory.')}
                >
                  <div>
                    <strong>Total Dioceses Processed</strong>
                    <div>{summary.total_dioceses_processed}</div>
                  </div>
                </OverlayTrigger>
              </Col>
              <Col>
                <OverlayTrigger
                  placement="top"
                  delay={{ show: 250, hide: 400 }}
                  overlay={(props) => renderTooltip(props, 'The number of dioceses for which a parish directory URL was successfully found.')}
                >
                  <div>
                    <strong>Parish Directories Found</strong>
                    <div>{summary.found_parish_directories}</div>
                  </div>
                </OverlayTrigger>
              </Col>
              <Col>
                <OverlayTrigger
                  placement="top"
                  delay={{ show: 250, hide: 400 }}
                  overlay={(props) => renderTooltip(props, 'The number of dioceses for which a parish directory URL could not be found.')}
                >
                  <div>
                    <strong>Parish Directories Not Found</strong>
                    <div>{summary.not_found_parish_directories}</div>
                  </div>
                </OverlayTrigger>
              </Col>
            </Row>
            <hr />
            <Row className="text-center">
              <Col>
                <OverlayTrigger
                  placement="bottom"
                  delay={{ show: 250, hide: 400 }}
                  overlay={(props) => renderTooltip(props, 'The total number of parishes extracted from all found parish directories.')}
                >
                  <div>
                    <strong>Parishes Extracted</strong>
                    <div>{summary.parishes_extracted}</div>
                  </div>
                </OverlayTrigger>
              </Col>
              <Col>
                <OverlayTrigger
                  placement="bottom"
                  delay={{ show: 250, hide: 400 }}
                  overlay={(props) => renderTooltip(props, 'The number of parishes for which schedule information (adoration or reconciliation) has been successfully extracted.')}
                >
                  <div>
                    <strong>Parishes with Data Extracted</strong>
                    <div>{summary.parishes_with_data_extracted}</div>
                  </div>
                </OverlayTrigger>
              </Col>
              <Col>
                <OverlayTrigger
                  placement="bottom"
                  delay={{ show: 250, hide: 400 }}
                  overlay={(props) => renderTooltip(props, 'The number of parishes for which schedule information could not be extracted.')}
                >
                  <div>
                    <strong>Parishes with Data Not Extracted</strong>
                    <div>{summary.parishes_with_data_not_extracted}</div>
                  </div>
                </OverlayTrigger>
              </Col>
            </Row>
          </div>
        )}

        <h2>Dioceses Data</h2>
        <p>Displaying the first 20 records from the database.</p>
        {loading && <Spinner animation="border" />}
        {error && <Alert variant="danger">Error fetching data: {error}</Alert>}
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
                    onClick={(e) => e.stopPropagation()} // Prevent sorting when clicking input
                    className="mt-1"
                  />
                </th>
                <th style={{ cursor: 'pointer' }}>
                  <div onClick={() => handleSort('Address')}>
                    Address {sortBy === 'Address' && (sortOrder === 'asc' ? '▲' : '▼')}
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
                  <div onClick={() => handleSort('Website')}>
                    Website {sortBy === 'Website' && (sortOrder === 'asc' ? '▲' : '▼')}
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
                <th>Parishes Directory</th>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('parishes_in_db_count')}>
                  Parishes Extracted {sortBy === 'parishes_in_db_count' && (sortOrder === 'asc' ? '▲' : '▼')}
                </th>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('parishes_with_data_extracted_count')}>
                  Parishes with Data Extracted {sortBy === 'parishes_with_data_extracted_count' && (sortOrder === 'asc' ? '▲' : '▼')}
                </th>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('is_blocked')}>
                  Blocked {sortBy === 'is_blocked' && (sortOrder === 'asc' ? '▲' : '▼')}
                </th>
              </tr>
            </thead>
            <tbody>
              {dioceses.map((diocese, index) => (
                <tr key={diocese.id || index}>
                  <td>{diocese.Name}</td>
                  <td>{diocese.Address}</td>
                  <td><a href={diocese.Website} target="_blank" rel="noopener noreferrer">{diocese.Website}</a></td>
                  <td>
                    {diocese.parish_directory_url && 
                        <a href={diocese.parish_directory_url} target="_blank" rel="noopener noreferrer">{diocese.parish_directory_url}</a>
                    }
                  </td>
                  <td>
                    <Link to={`/diocese?id=${diocese.id}`}>{diocese.parishes_in_db_count}</Link>
                  </td>
                  <td>
                    <Link to={`/diocese?id=${diocese.id}&filter=with_data`}>{diocese.parishes_with_data_extracted_count}</Link>
                  </td>
                  <td>
                    {diocese.respectful_automation_used ? (
                      <OverlayTrigger
                        placement="top"
                        delay={{ show: 250, hide: 400 }}
                        overlay={(props) => renderBlockingTooltip(props, diocese)}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          <input
                            type="checkbox"
                            checked={diocese.is_blocked || false}
                            readOnly
                            style={{
                              cursor: diocese.is_blocked ? 'help' : 'default',
                              accentColor: diocese.is_blocked ? '#dc3545' : '#28a745'
                            }}
                          />
                        </div>
                      </OverlayTrigger>
                    ) : (
                      <span style={{ color: '#6c757d', fontSize: '0.8em' }}>Not tested</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}

        {/* Pagination Controls */}
        {!loading && !error && totalPages > 1 && (
          <div className="d-flex justify-content-center mt-3">
            <Pagination>
              <Pagination.Prev onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))} disabled={currentPage === 1} />
              {paginationItems}
              <Pagination.Next onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))} disabled={currentPage === totalPages} />
            </Pagination>
          </div>
        )}

        <ParishList />

      </Container>

      
    </>
  );
}

export default App;
