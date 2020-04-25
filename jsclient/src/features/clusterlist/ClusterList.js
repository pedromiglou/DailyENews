import React, { useEffect, useState } from "react";
import clsx from "clsx";
import PropTypes from "prop-types";
import { connect } from "react-redux";
// material ui components
import { useTheme } from "@material-ui/core/styles";
import useMediaQuery from "@material-ui/core/useMediaQuery";
import CircularProgress from "@material-ui/core/CircularProgress";
import Paper from "@material-ui/core/Paper";
// jarr
import Cluster from "./components/Cluster";
import Content from "./components/Content";
import SelectedObjCard from "./components/SelectedObjCard";
import { doListClusters } from "./clusterSlice";
import makeStyles from "./components/style";


const filterClusters = (requestedClusterId, filter) => (cluster) => (
    // is selected cluster
    (requestedClusterId && requestedClusterId === cluster.id)
     // filters is on all
     || filter === "all"
     // cluster is not read and no filter
     || (!cluster.read && !filter)
     // cluster is liked and filtering on liked
     || (cluster.liked && filter === "liked")
);


function mapStateToProps(state) {
  let selectedFilterObj;
  if(state.clusters.filters["feed_id"]) {
    selectedFilterObj = state.feeds.feedListRows.filter((row) => (
      row.type === "feed" && row.id === state.clusters.filters["feed_id"]
    ))[0];
  } else if (state.clusters.filters["category_id"]) {
    selectedFilterObj = state.feeds.feedListRows.filter((row) => (
      row.type === "categ" && row.id === state.clusters.filters["category_id"]
    ))[0];
  }

  let clusters = [];
  if (!state.clusters.loading) {
    clusters = state.clusters.clusters.filter(
        filterClusters(state.clusters.requestedClusterId,
                       state.clusters.filters.filter)
    );
  }
  return { clusters,
           loadedCluster: state.clusters.loadedCluster,
           filters: state.clusters.filters,
           loading: state.clusters.loading,
           isShifted: state.feeds.isOpen && !state.edit.isOpen,
           selectedFilterObj,
  };
}

const mapDispatchToProps = (dispatch) => ({
  listClusters(filters) {
    return dispatch(doListClusters(filters));
  },
});


function ClusterList({ clusters, filters, loadedCluster,
                       loading, isShifted,
                       selectedFilterObj,
                       listClusters, openEditPanel,
                       }) {
  const theme = useTheme();
  const classes = makeStyles();
  const splitedMode = useMediaQuery(theme.breakpoints.up("md"));
  const contentClassName = clsx(classes.main,
    {[classes.mainShifted]: isShifted,
     [classes.mainSplitted]: splitedMode});
  const [everLoaded, setEverLoaded] = useState(false);
  useEffect(() => {
    if (!everLoaded) {
      setEverLoaded(true);
      listClusters(filters);
    }
  }, [everLoaded, filters, listClusters]);

  let list;
  if (loading) {
    list = <CircularProgress />;
  } else {
    list = clusters.map((cluster) => (
        <Cluster key={"c-" + cluster.id}
          cluster={cluster}
          splitedMode={splitedMode}
        />)
    );
  }
  let card;
  if (selectedFilterObj) {
    card = <SelectedObjCard
              id={selectedFilterObj.id}
              str={selectedFilterObj.str}
              type={selectedFilterObj.type}
              iconUrl={selectedFilterObj["icon_url"]}
              errorCount={selectedFilterObj["error_count"]}
              lastRetrieved={selectedFilterObj["last_retrieved"]}
            />;
  }
  if (!splitedMode) {
    return (
      <main className={contentClassName}>
        {card}
        {list}
      </main>
    );
  }
  return (
    <main className={contentClassName}>
      <div className={clsx(classes.clusterList,
                           {[classes.clusterListShifted]: isShifted,})}>
        {card}
        {list}
      </div>
      <Paper className={clsx(classes.contentPanel,
                           {[classes.contentPanelShifted]: isShifted,})}>
         <Content clusterId={loadedCluster.id} />
      </Paper>
    </main>
  );
}

ClusterList.propTypes = {
  clusters: PropTypes.array.isRequired,
  filters: PropTypes.object.isRequired,
  loading: PropTypes.bool.isRequired,
  listClusters: PropTypes.func.isRequired,
  selectedFilterObj: PropTypes.object,
};

export default connect(mapStateToProps, mapDispatchToProps)(ClusterList);