import React from "react";
import PropTypes from "prop-types";
import { connect } from "react-redux";

import { ThemeProvider } from "@mui/styles";

import {jarrTheme } from "./Jarr.theme";
import NoAuth from "./features/noauth/NoAuth";
import TopMenu from "./features/topmenu/TopMenu";
import FeedList from "./features/feedlist/FeedList";
import EditPanel from "./features/editpanel/EditPanel";
import ClusterList from "./features/clusterlist/ClusterList";

function mapStateToProps(state) {
  return { isLogged: !!state.auth.token, };
}

function Jarr({ isLogged }) {
  if (!isLogged) {
    return <ThemeProvider theme={jarrTheme}><NoAuth /></ThemeProvider>;
  }
  return (<ThemeProvider theme={jarrTheme}>
            <TopMenu />
            <FeedList />
            <ClusterList />
            <EditPanel />
          </ThemeProvider>);
}

Jarr.propTypes = {
  isLogged: PropTypes.bool.isRequired,
};

export default connect(mapStateToProps)(Jarr);
